"""Script de un solo uso: reconstruye la ESTRUCTURA (no los datos reales, todavía) del informe
financiero estático `informe-junio-2026-LCE.html` (LAARCOURIER EXPRESS, junio 2026) dentro del
dashboard "Administracion" (`dashboard_id='administracion'`), usando el sistema genérico de
dashboards ya existente — Zona Personal, `services/generic_charts.py`,
`services/dashboard_layout.py` — sin escribir ninguna función de cálculo nueva.

Fase 1 (esta corrida): cifras de junio 2026 transcritas del HTML como contenido FIJO — cada
KPI/gráfico/tabla se arma con un `DataFrame` en memoria de una sola fila por categoría, ya con el
valor final, así el pipeline de agregación (`generar_datos_grafica`/`generar_datos_multiserie`/
`generar_datos_multivalor`/`generar_datos_tabla`) hace un passthrough exacto sin necesitar ningún
archivo real. NO queda conectado a ninguna fuente de datos — no se actualiza solo. Fase 2 (fuera
de alcance de este script): conectar estos mismos componentes a un archivo tabular mensual real,
vía "Cargar otro archivo"/"Conectar vista de base de datos", una vez que exista ese archivo.

Las 7 secciones del informe original se combinan en 5 pestañas (límite `LIMITE_PESTANAS`):
1. Resumen Ejecutivo
2. Rentabilidad
3. Balance General
4. Caja, Deuda y Situación de Caja (secciones 4+7 combinadas)
5. Capital de Trabajo y Cartera (secciones 5+6 combinadas)

Aproximaciones deliberadas (sin equivalente exacto en `generic_charts.TIPOS_VISUALIZACION` ni en
`GenericDataTable`), documentadas también en el reporte final al usuario:
- Combinado barra+línea con doble eje Y → `lineas_multiples` (una sola escala).
- Cascada horizontal (EBITDA → Flujo Neto) → `barras_horizontales` simple, sin efecto "puente".
- Apiladas con positivos y negativos (Activos vs Pasivos) → `barras_apiladas`.
- Tablas jerárquicas con indentación/rowspan (Balance General, aging por cliente) → tabla plana.
- Párrafos largos a mano (Headlines, Hallazgos, Fortalezas/Oportunidades, notas al pie, >500
  caracteres) → varios bloques de texto encadenados, uno por punto/párrafo, texto VERBATIM del
  informe original (no el hallazgo autogenerado por `HallazgosClaveCard`).

Reutiliza `agregar_componente_generado`/`agregar_componente_presentacional` (públicas) para todo
lo que ya soportan tal cual; solo para bloques de texto con contenido propio (que
`agregar_componente_presentacional` no permite, siempre nace con un título/vacío por defecto) usa
un helper propio (`_agregar_bloque_texto`) que reutiliza las mismas piezas internas
(`_generar_component_id_unico`, `_escribir_componentes`) que ya usa esa función pública — mismo
patrón, con contenido propio.
"""

import pandas as pd
from django.core.management.base import BaseCommand

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from cartera.models import DashboardComponent
from cartera.services import dashboard_layout as dl
from cartera.services import dashboards as dashboards_service
from cartera.services import generic_charts

DASHBOARD_RAIZ = 'administracion'


def _agregar_bloque_texto(dashboard_id, tipo, titulo='', descripcion='', ancho_columnas=None, reemplazar_existentes=False):
    """Igual que `dashboard_layout.agregar_componente_presentacional`, pero con contenido propio
    (esa función pública siempre nace con un título por defecto/vacío, pensada para que el usuario
    lo edite después a mano desde el panel de propiedades — acá se necesita el texto final ya)."""
    layout = dl.obtener_o_crear_layout(dashboard_id)
    existentes = [] if reemplazar_existentes else list(dl.componentes_validos(dashboard_id).values())
    usados = {c['component_id'] for c in existentes}

    base_id = titulo or ('Título' if tipo == DashboardComponent.Tipo.TITLE else 'Separador')
    component_id = dl._generar_component_id_unico(base_id, usados)
    orden = len(existentes) + 1
    ancho = (12 // ancho_columnas) if ancho_columnas else dl.PRESENTACIONAL_ANCHO_DEFECTO
    nuevo = {
        'component_id': component_id, 'type': tipo, 'chart_type': '',
        'row': orden, 'order': orden, 'width': ancho, 'height': dl.PRESENTACIONAL_ALTO[tipo], 'is_visible': True,
        'content': {'titulo': titulo, 'descripcion': descripcion},
        'styles': {}, 'config': {'zona': 'personal'},
    }
    dl._escribir_componentes(layout, existentes + [nuevo])
    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])
    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_CHART_ADDED', actor=None,
        dashboard_id=dashboard_id, component_id=component_id, new_values=nuevo,
        metadata={'version': layout.version, 'reemplazo_existentes': reemplazar_existentes}, request=None,
    )
    return layout


class ConstructorDashboard:
    """Acumula componentes en la Zona Personal de UN dashboard/pestaña, en el orden en que se
    llaman sus métodos — el primer llamado limpia la plantilla fija de 13 posiciones con datos de
    ejemplo (`reemplazar_existentes=True`, mismo mecanismo que "primera gráfica tras cargar un
    archivo nuevo"), el resto se suma encima."""

    def __init__(self, dashboard_id):
        self.dashboard_id = dashboard_id
        self._primera = True

    def _consumir_primera(self):
        primera = self._primera
        self._primera = False
        return primera

    def titulo(self, texto):
        _agregar_bloque_texto(
            self.dashboard_id, DashboardComponent.Tipo.TITLE, titulo=texto,
            ancho_columnas=1, reemplazar_existentes=self._consumir_primera(),
        )

    def texto(self, texto, ancho_columnas=1):
        _agregar_bloque_texto(
            self.dashboard_id, DashboardComponent.Tipo.TEXT, descripcion=texto,
            ancho_columnas=ancho_columnas, reemplazar_existentes=self._consumir_primera(),
        )

    def kpi(self, titulo, valor, descripcion='', ancho_columnas=4):
        df = pd.DataFrame({'valor': [valor]})
        datos = generic_charts.generar_datos_grafica(df, 'valor', None)
        dl.agregar_componente_generado(
            self.dashboard_id,
            {'titulo': titulo, 'descripcion': descripcion, 'columna_valor': 'valor', 'datos': datos,
             'ancho_columnas': ancho_columnas, 'zona': 'personal'},
            reemplazar_existentes=self._consumir_primera(),
        )

    def barra(self, titulo, categorias, valores, chart_type='barras_verticales', descripcion='', ancho_columnas=2):
        df = pd.DataFrame({'categoria': categorias, 'valor': valores})
        datos = generic_charts.generar_datos_grafica(df, 'valor', 'categoria')
        dl.agregar_componente_generado(
            self.dashboard_id,
            {'titulo': titulo, 'descripcion': descripcion, 'columna_valor': 'valor', 'columna_categoria': 'categoria',
             'datos': datos, 'tipo_visualizacion': chart_type, 'ancho_columnas': ancho_columnas, 'zona': 'personal'},
            reemplazar_existentes=self._consumir_primera(),
        )

    def circular(self, titulo, categorias, valores, chart_type='dona', descripcion='', ancho_columnas=2):
        self.barra(titulo, categorias, valores, chart_type=chart_type, descripcion=descripcion, ancho_columnas=ancho_columnas)

    def multivalor(self, titulo, categorias, series, chart_type='lineas_multiples', descripcion='', ancho_columnas=2):
        """`series`: dict {nombre_serie: [valores...]} — varias columnas de valor sobre el mismo
        eje de categorías (`generar_datos_multivalor`), usado por `lineas_multiples`."""
        df = pd.DataFrame({'categoria': categorias, **series})
        datos = generic_charts.generar_datos_multivalor(df, 'categoria', list(series.keys()))
        dl.agregar_componente_generado(
            self.dashboard_id,
            {'titulo': titulo, 'descripcion': descripcion, 'columna_categoria': 'categoria',
             'columnas_valor': list(series.keys()), 'datos': datos, 'tipo_visualizacion': chart_type,
             'ancho_columnas': ancho_columnas, 'zona': 'personal'},
            reemplazar_existentes=self._consumir_primera(),
        )

    def multiserie(self, titulo, categorias, series, chart_type='barras_apiladas', descripcion='', ancho_columnas=2):
        """`series`: dict {nombre_serie: [valores...]} — una sola columna de valor partida por
        categoría (eje) × serie (leyenda/segmento), usado por barras_agrupadas/apiladas/área
        apilada (`generar_datos_multiserie`, formato "largo": una fila por combinación)."""
        filas = [
            {'categoria': cat, 'serie': serie, 'valor': valores[i]}
            for serie, valores in series.items() for i, cat in enumerate(categorias)
        ]
        df = pd.DataFrame(filas)
        datos = generic_charts.generar_datos_multiserie(df, 'valor', 'categoria', 'serie')
        dl.agregar_componente_generado(
            self.dashboard_id,
            {'titulo': titulo, 'descripcion': descripcion, 'columna_valor': 'valor', 'columna_categoria': 'categoria',
             'columna_serie': 'serie', 'datos': datos, 'tipo_visualizacion': chart_type,
             'ancho_columnas': ancho_columnas, 'zona': 'personal'},
            reemplazar_existentes=self._consumir_primera(),
        )

    def tabla(self, titulo, columna_id, filas, columnas_valor, descripcion='', ancho_columnas=1, columnas_texto=()):
        """`filas`: lista de dicts con `columna_id` + cada nombre en `columnas_valor` (numéricos,
        `tipo_agregacion` 'suma' por defecto — con 1 sola fila por id, la "suma" es un passthrough
        exacto del valor ya calculado). `columnas_valor` acá es solo la lista de nombres.
        `columnas_texto`: subconjunto de `columnas_valor` que en realidad es texto/categoría (p.
        ej. "62% ✓", "▲ +5.46 días") — se agrega como `tipo_agregacion='valor_celda'` en vez de
        sumar, mismo criterio que `generar_datos_tabla` para columnas no numéricas."""
        df = pd.DataFrame(filas)
        columnas_valor_spec = [
            {'columna': c, 'tipo_agregacion': 'valor_celda' if c in columnas_texto else 'suma'} for c in columnas_valor
        ]
        datos = generic_charts.generar_datos_tabla(df, columna_id, columnas_valor_spec, limite=len(filas))
        dl.agregar_componente_generado(
            self.dashboard_id,
            {'titulo': titulo, 'descripcion': descripcion, 'columna_id': columna_id,
             'columnas_valor': columnas_valor_spec, 'datos': datos, 'ancho_columnas': ancho_columnas, 'zona': 'personal'},
            reemplazar_existentes=self._consumir_primera(),
        )


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PESTAÑA 1 — RESUMEN EJECUTIVO
# ══════════════════════════════════════════════════════════════════════════════════════════════
def poblar_resumen_ejecutivo(c):
    c.kpi('Ingresos Junio', 2558101, '▼ -2.94% vs mayo')
    c.kpi('Margen Bruto', 20.79, '▼ -3.92pp vs mayo')
    c.kpi('Utilidad Neta', 117227, '▼ -49.94% vs mayo · 4.58%')
    c.kpi('Flujo Neto Caja', 128714, '▲ Revierte déficit de mayo')
    c.kpi('Deuda Bancaria', 1209695, '▼ -8.66% vs mayo')
    c.kpi('Utilidad Acum. YTD', 1003877, '▲ Ene–Jun 2026 · +78% vs presup.')

    c.titulo('Headlines del Mes')
    c.texto('01. Junio registra ingresos de $2,558,101, el segundo mes de menor facturación del semestre; retrocede -2.94% vs mayo (-$77,547), tras el fuerte ritmo de abril-mayo.')
    c.texto('02. Margen bruto cae a 20.79% (-3.92pp vs mayo, que había sido el máximo del semestre): los costos de transporte y fletes terrestres subieron cerca de $99.8K en el mes, mientras los ingresos retrocedieron.')
    c.texto('03. Utilidad neta $117,227 (4.58% de margen), -49.94% vs mayo; aun así, el acumulado YTD supera el millón de dólares ($1,003,877).')
    c.texto('04. Deuda bancaria total $1,209,695 (-$114,711 vs mayo, -8.66%), tras haberse más que triplicado entre marzo y mayo; cobertura de intereses 11.10x (vs 22.30x en mayo).')
    c.texto('05. Flujo neto de caja +$128,714 en junio (vs -$53,729 en mayo), explicado principalmente por un aumento de $250,131 en obligaciones por pagar no operativas (anticipos de clientes UPS/nacionales y obligaciones laborales, ver detalle en Caja & Deuda), ya que el flujo operativo del mes fue prácticamente neutro (-$613).')

    c.titulo('✅ Fortalezas')
    c.texto('Utilidad acumulada YTD supera el millón de dólares: $1,003,877 en el semestre, +78% sobre el presupuesto ($563,179 presupuestado, según Notas al Directorio de julio).')
    c.texto('Ventas del semestre por encima de lo proyectado: $15,987,391 reales vs $14,333,076 presupuestados (+12%).')
    c.texto('Flujo neto de caja revierte a positivo: +$128,714 en junio, tras el déficit de mayo (-$53,729), y la deuda bancaria retrocede -8.66% en el mes.')

    c.titulo('⚡ Oportunidades de Mejora')
    c.texto('Margen bruto retrocede a 20.79% (-3.92pp vs mayo): presionado por el alza de transporte y fletes terrestres (+$99.8K en el mes) — coherente con el alza de tarifas de combustible señalada por la Gerencia para el segundo semestre.')
    c.texto('Deuda bancaria en niveles elevados: se multiplicó por 3.5x entre marzo y mayo ($375K → $1.32M) y se mantiene en $1.21M pese a la baja de junio.')
    c.texto('Cartera por cobrar en gestión activa: 360 Lion mantiene un saldo de $209K tras un pago parcial de $102K (recibido el 3 de julio); Transexpress permanece en tratamiento con el Directorio y la oficina de Miami.')

    c.titulo('Síntesis del Informe')
    c.texto('📊 Rentabilidad — Margen bruto 20.79% (-3.92pp vs mayo); EBITDA $149,675 (5.85%). Utilidad neta YTD: $1,003,877.')
    c.texto('🏛 Balance — Activos totales $8.58M (+5.24% vs mayo), impulsados por CxC. Ratio corriente 1.23x. Patrimonio contable reducido a $101,631 por reclasificación de dividendos por pagar ($2.08M) desde abril; equity total (patrimonio + utilidad YTD): $1,105,508.')
    c.texto('💵 Caja & Deuda — Caja $1,456,198 (+$14,004). Deuda bancaria $1,209,695. Flujo operativo -$613; flujo neto +$128,714. D/E: 1.09x.')
    c.texto('⚙️ Capital de Trabajo — Ciclo (CxC−CxP, sin WIP) 35.53 días (+3.25 vs mayo). Capital de trabajo $3,380,740 (+$150,288). Cada $100 de ingreso anualizado requiere $11.01 de capital de trabajo.')

    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
    c.multivalor(
        'Evolución YTD — Ingresos y Utilidad Neta', meses,
        {'Ingresos ($)': [2519202, 2829500, 2656173, 2721202, 2635648, 2558101],
         'Utilidad Neta ($)': [111558, 147551, 210957, 182401, 234185, 117228]},
        chart_type='lineas_multiples',
        descripcion='Ingresos con mínimo en enero ($2.52M) y máximo en febrero ($2.83M); junio ($2.56M) retrocede -2.94% vs mayo. Utilidad neta de junio ($117.2K) vuelve a niveles similares a los de inicio de año, muy por debajo del máximo de mayo ($234.2K).',
    )
    c.multiserie(
        'Ingresos por Línea de Negocio — YTD ($)', meses,
        {'Courier Nacional (Total CB)': [1431049, 1608969, 1589890, 1751079, 1790611, 1848742],
         'Internacional (UPS/Laarbox/Temu)': [919042, 1071253, 933253, 785563, 618234, 504699],
         'Servicios Logísticos (3PL HYM)': [144504, 128104, 122309, 147158, 159017, 156091],
         'Servicios Especiales (Fletes/Pool)': [40671, 36170, 40441, 62783, 79502, 60610]},
        chart_type='barras_apiladas',
        descripcion='Courier Nacional (Total CB: Carga, Docs/Valija, Cod, Seguro, Pharma) concentra el 72.3% de los ingresos de junio ($1.85M) y crece de forma sostenida en el semestre. Internacional (UPS, Laarbox, Temu, 360 Lion) retrocede -45.1% desde enero ($919.0K → $504.7K), la mayor caída relativa del período.',
    )

    c.tabla(
        'Contribución al Margen Bruto Total por Línea de Negocio — Evolución YTD (% sobre ingresos totales)',
        'Línea',
        [
            {'Línea': 'Margen Bruto Total (Vista por Línea) %', 'Ene': 18.66, 'Feb': 18.21, 'Mar': 22.13, 'Abr': 20.97, 'May': 23.91, 'Jun': 19.87},
            {'Línea': 'Courier Nacional (Total CB)', 'Ene': 5.43, 'Feb': 5.96, 'Mar': 9.80, 'Abr': 13.77, 'May': 13.47, 'Jun': 12.15},
            {'Línea': 'Internacional (UPS/Laarbox/Temu)', 'Ene': 11.93, 'Feb': 11.57, 'Mar': 11.60, 'Abr': 5.45, 'May': 7.93, 'Jun': 5.89},
            {'Línea': 'Servicios Especiales (Fletes/Pool)', 'Ene': 0.25, 'Feb': 0.18, 'Mar': 0.23, 'Abr': 0.42, 'May': 0.55, 'Jun': 0.40},
            {'Línea': 'Servicios Logísticos (3PL HYM)', 'Ene': 1.06, 'Feb': 0.50, 'Mar': 0.49, 'Abr': 1.34, 'May': 1.95, 'Jun': 1.43},
        ],
        ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
        descripcion='Courier Nacional (línea core) más que duplicó su contribución al margen bruto entre enero (5.43%) y junio (12.15%). Internacional se mantiene muy por debajo de los niveles de inicio de año (5.89% en junio vs 11.93% en enero). Servicios Logísticos (3PL HYM) aporta 1.43% en junio, por debajo de su máximo del semestre (1.95% en mayo).',
    )
    c.texto('Nota: esta tabla proviene de la hoja "REAL 2026 PRESUPUESTO 2026" del Excel (vista por línea de negocio), que clasifica ciertos costos de forma distinta a la hoja "P y G 2026" (vista contable por tipo de gasto) — por eso el margen bruto total de esta vista (19.87% en junio) difiere del margen bruto consolidado reportado en el Cash Flow Story y usado como KPI (20.79%). Ambas fuentes concilian exactamente en la utilidad neta final ($117,227); el resto del informe usa el Cash Flow Story como fuente autorizada para las cifras consolidadas de P&G.')

    c.titulo('Recomendación del Mes — Jul 2026')
    c.texto('"Priorizar la cobranza de cartera vencida (360 Lion: saldo $209K; Transexpress: en tratamiento) para sostener la conversión de utilidad a caja."')


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PESTAÑA 2 — RENTABILIDAD
# ══════════════════════════════════════════════════════════════════════════════════════════════
def poblar_rentabilidad(c):
    c.kpi('Ingresos', 2558101, '▼ -2.94% vs mayo')
    c.kpi('Margen Bruto', 20.79, '▼ -3.92pp vs mayo')
    c.kpi('EBITDA', 149675, '▼ 5.85% de margen')
    c.kpi('Utilidad Neta', 117227, '▼ 4.58% · -49.94% vs may')
    c.kpi('Cob. Intereses', 11.10, '▼ -11.20x vs mayo')

    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
    c.multivalor(
        'Evolución de Márgenes YTD (%)', meses,
        {'Margen Bruto %': [19.52, 19.13, 22.84, 21.73, 24.71, 20.79],
         'Margen Operacional %': [4.36, 4.71, 7.69, 6.63, 9.21, 4.99],
         'Margen Neto %': [4.43, 5.21, 7.94, 6.70, 8.89, 4.58]},
        chart_type='lineas_multiples',
        descripcion='El margen bruto alcanzó su máximo del semestre en mayo (24.71%) y retrocede a 20.79% en junio (-3.92pp). El margen neto sigue el mismo patrón: máximo en mayo (8.89%) y en junio (4.58%) regresa a niveles similares a los de enero-febrero.',
    )
    c.multivalor(
        'Margen Bruto % vs Capital de Trabajo por $100', meses,
        {'Margen Bruto %': [19.52, 19.13, 22.84, 21.73, 24.71, 20.79],
         'CT por $100 de ingresos ($)': [11.27, 7.89, 8.09, 9.00, 10.21, 11.01]},
        chart_type='lineas_multiples',
        descripcion='El capital de trabajo por cada $100 de ingresos subió a $11.01 en junio (desde $10.21 en mayo), impulsado por el crecimiento de CxC, y se acerca al nivel más alto del semestre ($11.27 en enero). El margen bruto retrocedió en el mismo período (-3.92pp), evidenciando una combinación desfavorable de mayor capital inmovilizado y menor rentabilidad. Nota: en el informe original estas 2 series usan doble eje Y (escalas muy distintas, % vs $) — acá comparten un solo eje por limitación del editor de dashboards.',
    )

    c.tabla(
        'Estado de Resultados Resumido — Junio vs Mayo 2026', 'Concepto',
        [
            {'Concepto': 'Total Ingresos Operacionales', 'Junio 2026': 2558101, 'Mayo 2026': 2635648, 'Var. $': -77547, 'Var. %': -2.94},
            {'Concepto': 'Costos Directos (Gastos de Operación)', 'Junio 2026': 2026274, 'Mayo 2026': 1984335, 'Var. $': 41939, 'Var. %': 2.11},
            {'Concepto': 'Utilidad Bruta', 'Junio 2026': 531828, 'Mayo 2026': 651313, 'Var. $': -119485, 'Var. %': -18.35},
            {'Concepto': 'Gastos Administrativos', 'Junio 2026': 256915, 'Mayo 2026': 262488, 'Var. $': -5573, 'Var. %': -2.12},
            {'Concepto': 'Gastos de Ventas', 'Junio 2026': 147381, 'Mayo 2026': 146173, 'Var. $': 1208, 'Var. %': 0.83},
            {'Concepto': 'Utilidad Operacional', 'Junio 2026': 127532, 'Mayo 2026': 242652, 'Var. $': -115120, 'Var. %': -47.44},
            {'Concepto': 'Gastos Financieros (Interés)', 'Junio 2026': 11485, 'Mayo 2026': 10884, 'Var. $': 601, 'Var. %': 5.52},
            {'Concepto': 'Otros Ingresos No Operacionales', 'Junio 2026': 1181, 'Mayo 2026': 2417, 'Var. $': -1236, 'Var. %': -51.14},
            {'Concepto': 'Resultado Antes de Impuestos', 'Junio 2026': 117228, 'Mayo 2026': 234185, 'Var. $': -116957, 'Var. %': -49.94},
        ],
        ['Junio 2026', 'Mayo 2026', 'Var. $', 'Var. %'],
        descripcion='Fuente: Excel Consolidado, hoja "P y G 2026" (detallada por tipo de gasto). Concilia con el Cash Flow Story, fuente autorizada para las cifras consolidadas de P&G de junio (Ingresos $2,558,101; Margen Bruto 20.79%; Utilidad Operacional $127,531; Utilidad Neta $117,227) — diferencia menor de $1 atribuible a redondeo.',
    )

    c.titulo('↑ ¿Por qué subieron los costos directos? — +$41,939 (+2.11%)')
    c.tabla(
        'Detalle por tipo de gasto — Costos Directos', 'Tipo de Costo',
        [
            {'Tipo de Costo': 'Transporte y fletes terrestres (principal driver)', 'May 2026': 532760, 'Jun 2026': 601318, 'Δ $': 68559},
            {'Tipo de Costo': 'Transporte y fletes terrestres (Nacional)', 'May 2026': 190913, 'Jun 2026': 212681, 'Δ $': 21768},
            {'Tipo de Costo': 'Transporte y fletes terrestres (Rima)', 'May 2026': 86647, 'Jun 2026': 106052, 'Δ $': 19405},
            {'Tipo de Costo': 'Personal - Sueldos', 'May 2026': 269939, 'Jun 2026': 279574, 'Δ $': 9635},
            {'Tipo de Costo': 'Pesajes y bodegajes en aduana', 'May 2026': 43225, 'Jun 2026': 10275, 'Δ $': -32950},
            {'Tipo de Costo': 'Gastos UPS (diversos)', 'May 2026': 142194, 'Jun 2026': 122720, 'Δ $': -19474},
            {'Tipo de Costo': 'Transporte FLETES terrestres', 'May 2026': 48365, 'Jun 2026': 37087, 'Δ $': -11278},
        ],
        ['May 2026', 'Jun 2026', 'Δ $'],
    )
    c.texto('El transporte y fletes terrestres (en sus distintas cuentas) es el driver principal del alza, coherente con lo señalado por la Gerencia sobre el impacto de las tarifas de combustible en el segundo semestre. Pesajes/bodegajes y gastos UPS se contrajeron, compensando parcialmente. Detalle a nivel de cuenta contable (hoja "P y G 2026"); el resto de la variación corresponde a partidas menores.')

    c.titulo('↓ ¿Por qué bajaron los gastos administrativos? — -$5,573 (-2.12%)')
    c.tabla(
        'Detalle por rubro — Gastos Administrativos', 'Rubro',
        [
            {'Rubro': 'Impuesto Capital en Giro (no recurrente en mayo)', 'May 2026': 10332, 'Jun 2026': 0, 'Δ $': -10332},
            {'Rubro': 'Suministros de computación', 'May 2026': 13430, 'Jun 2026': 2717, 'Δ $': -10713},
            {'Rubro': 'Diversos - Otros', 'May 2026': 4041, 'Jun 2026': 14394, 'Δ $': 10353},
            {'Rubro': 'Afiliaciones - Otros', 'May 2026': 300, 'Jun 2026': 2930, 'Δ $': 2630},
            {'Rubro': 'Gasto de viaje - Pasajes aéreos', 'May 2026': 4761, 'Jun 2026': 6505, 'Δ $': 1744},
        ],
        ['May 2026', 'Jun 2026', 'Δ $'],
    )
    c.texto('Un cargo no recurrente de impuesto de capital en giro registrado en mayo ($10,332) no se repitió en junio, explicando gran parte de la baja. Suministros de computación también se redujo. Estas bajas compensaron el alza en partidas diversas y de viaje.')

    c.tabla(
        'Ratios de Rentabilidad — Ene-26 a Jun-26', 'Ratio',
        [
            {'Ratio': 'Margen Bruto %', 'Ene-26': 19.52, 'Feb-26': 19.13, 'Mar-26': 22.84, 'Abr-26': 21.73, 'May-26': 24.71, 'Jun-26': 20.79},
            {'Ratio': 'Margen EBITDA %', 'Ene-26': 0, 'Feb-26': 0, 'Mar-26': 8.46, 'Abr-26': 7.43, 'May-26': 10.03, 'Jun-26': 5.85},
            {'Ratio': 'Margen Neto %', 'Ene-26': 4.43, 'Feb-26': 5.21, 'Mar-26': 7.94, 'Abr-26': 6.70, 'May-26': 8.89, 'Jun-26': 4.58},
            {'Ratio': 'ROE % (anualizado)', 'Ene-26': 0, 'Feb-26': 0, 'Mar-26': 0, 'Abr-26': 290.29, 'May-26': 284.36, 'Jun-26': 127.25},
            {'Ratio': 'ROA % (anualizado)', 'Ene-26': 0, 'Feb-26': 0, 'Mar-26': 0, 'Abr-26': 30.34, 'May-26': 35.70, 'Jun-26': 17.83},
            {'Ratio': 'Cobertura Intereses', 'Ene-26': 15.71, 'Feb-26': 24.41, 'Mar-26': 45.11, 'Abr-26': 38.55, 'May-26': 22.30, 'Jun-26': 11.10},
        ],
        ['Ene-26', 'Feb-26', 'Mar-26', 'Abr-26', 'May-26', 'Jun-26'],
        descripcion='Los valores en 0 corresponden a "—" en el informe original (Margen EBITDA no disponible en Ene-Feb; ROE/ROA no disponibles en Ene-Mar, por no contar con equity/activos comparables previos al ajuste de dividendos de abril) — no son ceros reales. ROE y ROA = (Utilidad Operacional o Neta del mes × 12) / Equity o Activos Totales del cierre de mes, metodología del Cash Flow Story.',
    )


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PESTAÑA 3 — BALANCE GENERAL
# ══════════════════════════════════════════════════════════════════════════════════════════════
def poblar_balance_general(c):
    c.kpi('Total Activos', 8584187, '▲ +5.24% vs mayo')
    c.kpi('Activos Corrientes', 7583522, '88.3% del activo total')
    c.kpi('Total Pasivos', 7478679, '▲ +$310,117 vs mayo')
    c.kpi('Equity (Patrim. + Ut. YTD)', 1105508, 'Patrimonio $101,631 + Ut. YTD $1,003,877')
    c.kpi('Ratio Corriente', 1.23, '▲ +0.01x vs mayo')

    c.tabla(
        'Balance General Clave (USD) — Mar-26 a Jun-26', 'Cuenta',
        [
            {'Cuenta': 'ACTIVO CORRIENTE', 'Mar-26': 6913549, 'Abr-26': 5915884, 'May-26': 7153934, 'Jun-26': 7583522},
            {'Cuenta': 'Caja y Bancos', 'Mar-26': 790619, 'Abr-26': 524323, 'May-26': 1442194, 'Jun-26': 1456198},
            {'Cuenta': 'Inversiones Financieras CP', 'Mar-26': 328849, 'Abr-26': 29587, 'May-26': 29704, 'Jun-26': 29812},
            {'Cuenta': 'CxC Comerciales', 'Mar-26': 3966226, 'Abr-26': 4362125, 'May-26': 4551679, 'Jun-26': 4876663},
            {'Cuenta': 'Otras CxC (anticipos, IR, reclamos)', 'Mar-26': 1827856, 'Abr-26': 999849, 'May-26': 1130357, 'Jun-26': 1220849},
            {'Cuenta': 'ACTIVO NO CORRIENTE', 'Mar-26': 1012774, 'Abr-26': 1026085, 'May-26': 1002910, 'Jun-26': 1000665},
            {'Cuenta': 'PPE Neto', 'Mar-26': 663184, 'Abr-26': 685341, 'May-26': 670663, 'Jun-26': 668418},
            {'Cuenta': 'Otros Activos (intangibles, garantías)', 'Mar-26': 349590, 'Abr-26': 340744, 'May-26': 332247, 'Jun-26': 332247},
            {'Cuenta': 'TOTAL ACTIVOS', 'Mar-26': 7926323, 'Abr-26': 6941969, 'May-26': 8156844, 'Jun-26': 8584187},
            {'Cuenta': 'PASIVO CORRIENTE', 'Mar-26': 4411947, 'Abr-26': 5317865, 'May-26': 5867022, 'Jun-26': 6172010},
            {'Cuenta': 'Oblig. Financieras CP', 'Mar-26': 260771, 'Abr-26': 238185, 'May-26': 783888, 'Jun-26': 669178},
            {'Cuenta': 'Proveedores (CxP)', 'Mar-26': 1388510, 'Abr-26': 1423310, 'May-26': 1321227, 'Jun-26': 1495923},
            {'Cuenta': 'Otras CxP (incl. dividendos $2.08M)', 'Mar-26': 1457456, 'Abr-26': 2754507, 'May-26': 2771689, 'Jun-26': 2956031},
            {'Cuenta': 'Oblig. Laborales CP', 'Mar-26': 1275125, 'Abr-26': 871778, 'May-26': 960133, 'Jun-26': 1020794},
            {'Cuenta': 'PASIVO NO CORRIENTE', 'Mar-26': 865436, 'Abr-26': 870008, 'May-26': 1301540, 'Jun-26': 1306669},
            {'Cuenta': 'Oblig. Laborales LP', 'Mar-26': 750816, 'Abr-26': 755389, 'May-26': 761023, 'Jun-26': 766151},
            {'Cuenta': 'Oblig. Financieras LP', 'Mar-26': 114620, 'Abr-26': 114620, 'May-26': 540517, 'Jun-26': 540517},
            {'Cuenta': 'PATRIMONIO', 'Mar-26': 2178876, 'Abr-26': 101631, 'May-26': 101631, 'Jun-26': 101631},
            {'Cuenta': 'Utilidad Ejercicio 2026 YTD', 'Mar-26': 470064, 'Abr-26': 652465, 'May-26': 886650, 'Jun-26': 1003877},
            {'Cuenta': 'TOTAL PAS. + PATR. + UTIL.', 'Mar-26': 7926323, 'Abr-26': 6941969, 'May-26': 8156844, 'Jun-26': 8584187},
        ],
        ['Mar-26', 'Abr-26', 'May-26', 'Jun-26'], ancho_columnas=1,
        descripcion='El patrimonio contable se redujo de $2,178,876 (marzo) a $101,631 a partir de abril por la reclasificación de dividendos/participaciones por pagar ($2,077,245) hacia "Otras Cuentas por Pagar" — evento contable, no operativo. LCE no mantiene inventarios/WIP (negocio de servicios courier). Nota: esta tabla mezcla subtotales/totales con sus componentes como filas planas (sin indentación) — limitación del componente de tabla genérica; la columna "% del total" y la fila "Total" que agrega automáticamente no tienen un significado financiero preciso acá, ignorarlas.',
    )

    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
    c.multiserie(
        'Activos vs Pasivos — Evolución Ene-26 a Jun-26 (USD)', meses,
        {'Activos Ctes.': [7263257, 7545435, 6913549, 5915884, 7153934, 7583522],
         'Activos No Ctes.': [824082, 918236, 1012774, 1026085, 1002910, 1000665],
         'Pasivos Ctes.': [-4937577, -5160113, -4411947, -5317865, -5867022, -6172010],
         'Pasivos No Ctes.': [-859328, -865573, -865436, -870008, -1301540, -1306669]},
        chart_type='barras_apiladas',
        descripcion='Los activos crecieron $427K (+5.24%) en junio, impulsados principalmente por CxC (+$325K). Los pasivos corrientes también subieron ($305K), reflejando el mayor financiamiento de proveedores (CxP +$174.7K) y el crecimiento de otras cuentas por pagar. Las obligaciones laborales LP ($766K) y financieras LP ($541K) son los pasivos estructurales de largo plazo. Nota: en el original, activos y pasivos se apilan en direcciones opuestas del eje (positivo/negativo) para verse como "espejo" — acá los pasivos se cargan como valores negativos, pero el editor los apila igual que los positivos.',
    )


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PESTAÑA 4 — CAJA, DEUDA Y SITUACIÓN DE CAJA (secciones 4 + 7 combinadas)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def poblar_caja_deuda(c):
    c.kpi('Caja Junio', 1456198, '▲ +$14,004 en el mes')
    c.kpi('Deuda Bancaria', 1209695, '▼ -8.66% vs mayo')
    c.kpi('Caja Neta (Caja − Deuda)', 246503, '▲ +$128,715 vs mayo')
    c.kpi('Flujo Operativo', -613, '▼ vs $150,150 en mayo')
    c.kpi('Flujo Neto Caja', 128714, '▲ Revierte déficit de mayo')
    c.kpi('CxC (Cartera) — Impacto en Caja', -324984, '▼ Principal driver del mes')

    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
    c.multivalor(
        'Evolución Caja y Deuda Bancaria — Ene-26 a Jun-26', meses,
        {'Caja ($)': [804777, 1784313, 790619, 524323, 1442194, 1456198],
         'Deuda Bancaria Total ($)': [431249, 409015, 375390, 352805, 1324406, 1209695]},
        chart_type='lineas_multiples',
        descripcion='La caja se recuperó levemente en junio (+$14,004), tras el fuerte repunte de mayo. La deuda bancaria, que se había más que triplicado entre marzo y mayo ($375K → $1.32M) por nuevos desembolsos de corto y largo plazo, retrocede -8.66% en junio ($1.21M).',
    )

    c.titulo('De EBITDA a Flujo Neto de Caja — Junio 2026')
    c.barra(
        'De EBITDA a Flujo Neto de Caja — Junio 2026',
        ['EBITDA', 'CxC (Cartera)', 'CxP', 'Fl. Operativo', 'CAPEX+Interés+Extraord.', 'Anticipos Clientes+Oblig. Laborales', 'Fl. Neto de Caja'],
        [149675, -324984, 174696, -613, -30203, 159531, 128714],
        chart_type='barras_horizontales', ancho_columnas=1,
        descripcion='De los $149,675 de EBITDA generados, la cartera (CxC) absorbió $324,984 — más de dos veces el EBITDA del mes. Sin el aumento no operativo de $250,131 en anticipos de clientes y obligaciones laborales por pagar (neto de $90,600 de otras cuentas por cobrar), el flujo neto de caja habría sido negativo. Nota: en el original este es un gráfico de "cascada" (cada barra flota desde el acumulado anterior) — acá se muestra como barras simples con el valor de cada componente (con su signo), sin el efecto visual de "puente".',
    )
    c.tabla(
        'Desglose Flujo de Caja — Junio 2026 (detalle granular)', 'Concepto',
        [
            {'Concepto': 'EBITDA / Utilidad Op. de Caja (base)', 'Monto': 149675},
            {'Concepto': '↑ CxC: cobros < ingresos generados', 'Monto': -324984},
            {'Concepto': 'WIP: no aplica (negocio sin inventario)', 'Monto': 0},
            {'Concepto': '↑ CxP: proveedores financian más', 'Monto': 174696},
            {'Concepto': '= Flujo Operativo de Caja', 'Monto': -613},
            {'Concepto': '− Adquisición activos fijos (CAPEX)', 'Monto': -19899},
            {'Concepto': '− Interés pagado', 'Monto': -11485},
            {'Concepto': '+ Ingresos extraordinarios', 'Monto': 1181},
            {'Concepto': '+ Variación neta de otras cuentas de balance', 'Monto': 159531},
            {'Concepto': '− Capital retirado', 'Monto': -1},
            {'Concepto': '= Flujo Neto de Caja', 'Monto': 128714},
        ],
        ['Monto'], ancho_columnas=1,
        descripcion='Cómo se originó el flujo neto de caja de +$128,714 (fuente: Cash Flow Story, "Profit vs Cash Flow"). El flujo operativo de -$613 (prácticamente neutro) refleja una conversión mucho más débil que en mayo, explicada por el fuerte crecimiento de CxC (-$325K), solo parcialmente compensado por el mayor financiamiento de proveedores (+$174.7K).',
    )
    c.tabla(
        'Componente de Capital de Trabajo — Variación de Caja May→Jun', 'Componente CT',
        [
            {'Componente CT': 'CxC (↑ usa caja)', 'May-26': 4551679, 'Jun-26': 4876663, 'Var. Caja': -324984},
            {'Componente CT': 'WIP (no aplica)', 'May-26': 0, 'Jun-26': 0, 'Var. Caja': 0},
            {'Componente CT': 'CxP (↑ libera caja)', 'May-26': 1321227, 'Jun-26': 1495923, 'Var. Caja': 174696},
        ],
        ['May-26', 'Jun-26', 'Var. Caja'],
        descripcion='Total inversión en capital de trabajo (CxC + WIP − CxP): -$150,288 en el mes.',
    )

    c.titulo('¿Qué es la "Variación Neta de Otras Cuentas de Balance" de +$159,531?')
    c.texto('Es el efecto neto en caja de todas las cuentas del balance que NO son caja, deuda bancaria, CxC, CxP, WIP ni activo fijo — anticipos, retenciones, obligaciones laborales y otros saldos por cobrar/pagar de operaciones internas. Cuando estas cuentas de pasivo crecen más rápido que las de activo, el efecto neto libera caja — y eso fue lo que ocurrió en junio.')
    c.tabla(
        '↑ Otros Pasivos que crecieron (liberan caja): +$250,131', 'Cuenta (Balance General)',
        [
            {'Cuenta (Balance General)': 'Anticipo Clientes UPS', 'May-26': 130470, 'Jun-26': 218445, 'Δ $': 87975},
            {'Cuenta (Balance General)': 'Oblig. y Provisiones Laborales (CP)', 'May-26': 960133, 'Jun-26': 1020794, 'Δ $': 60661},
            {'Cuenta (Balance General)': 'Anticipo Clientes Nacionales', 'May-26': 28057, 'Jun-26': 53949, 'Δ $': 25892},
            {'Cuenta (Balance General)': 'IVA por Pagar', 'May-26': 276862, 'Jun-26': 294761, 'Δ $': 17899},
            {'Cuenta (Balance General)': 'Depósitos no Identificados', 'May-26': 63005, 'Jun-26': 80340, 'Δ $': 17335},
            {'Cuenta (Balance General)': 'Cuentas por Pagar - Otros', 'May-26': 76464, 'Jun-26': 97036, 'Δ $': 20572},
            {'Cuenta (Balance General)': 'Retención en la Fuente IR (por pagar)', 'May-26': 77123, 'Jun-26': 86305, 'Δ $': 9182},
            {'Cuenta (Balance General)': 'Oblig. Laborales (Largo Plazo)', 'May-26': 761023, 'Jun-26': 766151, 'Δ $': 5128},
            {'Cuenta (Balance General)': 'Fondos a Disposición', 'May-26': 42290, 'Jun-26': 47443, 'Δ $': 5153},
            {'Cuenta (Balance General)': 'Reembolsos Cajas Chicas', 'May-26': 173, 'Jun-26': 507, 'Δ $': 334},
            {'Cuenta (Balance General)': 'Dividendos por Pagar', 'May-26': 2077245, 'Jun-26': 2077245, 'Δ $': 0},
        ],
        ['May-26', 'Jun-26', 'Δ $'],
    )
    c.tabla(
        '↓ Otros Activos que crecieron (usan caja): -$90,600', 'Cuenta (Balance General)',
        [
            {'Cuenta (Balance General)': 'Retención en la Fuente IR (por cobrar)', 'May-26': 253938, 'Jun-26': 288617, 'Δ $': 34679},
            {'Cuenta (Balance General)': 'Cuentas por Cobrar a Trabajadores', 'May-26': 7072, 'Jun-26': 27695, 'Δ $': 20623},
            {'Cuenta (Balance General)': 'Reclamos', 'May-26': 78331, 'Jun-26': 98165, 'Δ $': 19834},
            {'Cuenta (Balance General)': 'Anticipos y Avances (entregados)', 'May-26': 730134, 'Jun-26': 745490, 'Δ $': 15356},
            {'Cuenta (Balance General)': 'Inversiones Financieras CP', 'May-26': 29704, 'Jun-26': 29812, 'Δ $': 108},
            {'Cuenta (Balance General)': 'Depósitos (garantías entregadas)', 'May-26': 41921, 'Jun-26': 41921, 'Δ $': 0},
            {'Cuenta (Balance General)': 'IVA por Cobrar', 'May-26': 18962, 'Jun-26': 18962, 'Δ $': 0},
        ],
        ['May-26', 'Jun-26', 'Δ $'],
    )
    c.texto('El efecto neto (+$250,131 de otros pasivos − $90,600 de otros activos = +$159,531) NO proviene de una venta de activos ni de una mejora operativa: se explica principalmente por el crecimiento de anticipos recibidos de clientes UPS y nacionales ($113,867 combinados) y por el aumento de obligaciones laborales por pagar ($65,789 combinados CP+LP). Los dividendos por pagar ($2,077,245) no tuvieron movimiento en el mes.')
    c.texto('Metodología: "Otros Pasivos" = Total Pasivos − Proveedores (CxP) − Deuda Bancaria. "Otros Activos" = Total Activos − Caja − CxC Comerciales − WIP. Reproduce el componente "Other Net Assets" del Cash Flow Story ($250,131 − $90,600 = $159,531). Fuente: Excel Consolidado, hoja "BG abierto".')

    c.titulo('Resumen Ejecutivo — Qué Explica la Posición de Caja de Junio')
    c.texto('01. La cartera (CxC) fue, con diferencia, el principal factor que explica el resultado de caja del mes. El crecimiento de cuentas por cobrar (+$324,984, de $4,551,679 a $4,876,663) consumió prácticamente toda la generación de EBITDA ($149,675), dejando un flujo operativo casi nulo (-$613).')
    c.texto('02. El financiamiento de proveedores (CxP +$174,696) amortiguó parcialmente el efecto de la cartera, pero no fue suficiente para compensarlo por completo.')
    c.texto('03. El flujo neto de caja del mes (+$128,714) resultó positivo no por la operación, sino por un aumento de $250,131 en obligaciones por pagar no operativas — principalmente anticipos recibidos de clientes UPS/nacionales ($113,867) y obligaciones laborales por pagar acumuladas ($65,789), parcialmente compensado por $90,600 de crecimiento en otras cuentas por cobrar. No debe interpretarse como mejora estructural de la conversión de utilidad a caja.')
    c.texto('04. Los dos mayores deudores, Transexpress ($428K) y Lion Ecommerce Logistics ($312K), concentran el 21.84% de la cartera total. Transexpress tiene 64% de su saldo vencido a más de 120 días (subió de $250,000 a $275,467 en el mes) y Lion Ecommerce tiene el 100% de su saldo vencido, aunque en mora reciente.')
    c.texto('05. El tramo de cartera "más de 120 días" ($354,864, 10% del portafolio) excede su meta de control (máximo 5%), y junto con el 19% en el tramo de 30 días, representa la principal palanca de mejora de caja disponible para julio.')
    c.texto('06. La deuda bancaria retrocedió -8.66% en el mes ($1,209,695, desde $1,324,406), reduciendo la carga financiera futura, aunque se mantiene en niveles elevados tras haberse más que triplicado entre marzo y mayo.')

    c.tabla(
        'Cartera — Dos Mayores Deudores, Situación a Junio 2026', 'Detalle',
        [
            {'Detalle': 'Lion Ecommerce Logistics — 30 días', 'Saldo': 153045, '%': 49},
            {'Detalle': 'Lion Ecommerce Logistics — 60 días', 'Saldo': 158714, '%': 51},
            {'Detalle': 'Lion Ecommerce Logistics — Total', 'Saldo': 311759, '%': 100},
            {'Detalle': 'Transexpress — Anticipada', 'Saldo': 84104, '%': 20},
            {'Detalle': 'Transexpress — 30 días', 'Saldo': 66079, '%': 15},
            {'Detalle': 'Transexpress — 60 días', 'Saldo': 2526, '%': 1},
            {'Detalle': 'Transexpress — Más 120 días', 'Saldo': 275467, '%': 64},
            {'Detalle': 'Transexpress — Total', 'Saldo': 428176, '%': 80},
            {'Detalle': 'Total ambos clientes (21.84% de la cartera)', 'Saldo': 739935, '%': 100},
        ],
        ['Saldo', '%'], ancho_columnas=1,
        descripcion='Entre los dos concentran $739,935 (21.84%) de la cartera total. Lion Ecommerce tiene el 100% de su saldo vencido, aunque en mora reciente (30-60 días). Transexpress tiene el 64% de su saldo en mora de más de 120 días — el tramo de mayor riesgo de incobrabilidad. (Tabla original con filas agrupadas por cliente vía rowspan; acá el nombre del cliente se repite en cada fila.)',
    )

    c.tabla(
        'Caja, Deuda y Capital de Trabajo — Sensibilidad Directa a Cartera', 'Indicador',
        [
            {'Indicador': 'CxC (Cartera Comercial)', 'Mayo': 4551679, 'Junio': 4876663, 'Variación': 324984},
            {'Indicador': 'Días CxC', 'Mayo': 52.53, 'Junio': 57.99, 'Variación': 5.46},
            {'Indicador': 'Flujo Operativo de Caja', 'Mayo': 150150, 'Junio': -613, 'Variación': -150763},
            {'Indicador': 'Caja', 'Mayo': 1442194, 'Junio': 1456198, 'Variación': 14004},
            {'Indicador': 'Deuda Bancaria', 'Mayo': 1324406, 'Junio': 1209695, 'Variación': -114711},
            {'Indicador': 'Cobertura de Intereses', 'Mayo': 22.30, 'Junio': 11.10, 'Variación': -11.20},
        ],
        ['Mayo', 'Junio', 'Variación'],
        descripcion='El deterioro de la cobertura de intereses (-11.20x) y del flujo operativo (-$150,763) tienen la misma raíz: el crecimiento de la cartera sin una recuperación equivalente en cobranza. La caja se mantuvo estable solo por el efecto no operativo señalado arriba, no por la generación propia del negocio.',
    )

    c.titulo('Recomendación del Mes — Situación de Caja')
    c.texto('"Condicionar la mejora sostenida de caja a la recuperación activa de cartera vencida (Transexpress y tramo +120 días) antes de asumir nuevo financiamiento bancario."')


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PESTAÑA 5 — CAPITAL DE TRABAJO Y CARTERA (secciones 5 + 6 combinadas)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def poblar_capital_cartera(c):
    c.kpi('Capital de Trabajo', 3380740, '▲ +$150,288 vs mayo')
    c.kpi('CxC Comerciales', 4876663, '57.99 días')
    c.kpi('WIP / Inventarios', 0, 'No aplica — negocio sin inventario')
    c.kpi('CxP Comerciales', 1495923, '22.46 días')
    c.kpi('Días Ciclo Efectivo', 35.53, '▲ +3.25 días vs mayo')

    meses4 = ['Mar-26', 'Abr-26', 'May-26', 'Jun-26']
    c.multivalor(
        'Días de Capital de Trabajo — Mar a Jun 2026', meses4,
        {'Días CxC': [45.42, 48.76, 52.53, 57.99], 'Días WIP': [0, 0, 0, 0],
         'Días CxP': [20.61, 20.33, 20.25, 22.46], 'Días Ciclo': [24.81, 28.43, 32.28, 35.53]},
        chart_type='lineas_multiples',
        descripcion='Los días de capital de trabajo suben a 35.53 en junio, cerca del nivel más alto del semestre (36.99 en enero), arrastrados por el aumento de días CxC (57.99, también cerca del máximo de enero) — solo parcialmente compensado por el alza en días CxP (22.46, máximo del semestre). No hay días WIP al no manejar inventario.',
    )
    meses6 = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
    c.multiserie(
        'Componentes Capital de Trabajo en USD — Ene-26 a Jun-26', meses6,
        {'CxC Comerciales': [4824613, 4132117, 3966226, 4362125, 4551679, 4876663],
         'CxP Comerciales': [1417500, 1454280, 1388510, 1423310, 1321227, 1495923]},
        chart_type='barras_agrupadas',
        descripcion='Las CxC alcanzaron su máximo del semestre en junio ($4.88M, +$325K vs mayo), tras una tendencia sostenida al alza desde marzo. Las CxP acompañaron con su propio máximo del período ($1.50M, +$175K).',
    )

    c.titulo('Ciclo de Conversión de Efectivo — Junio 2026')
    c.texto('Días WIP (0.00) + Días CxC (57.99) − Días CxP (22.46) = Días Ciclo (35.53). Cada $100 de ingreso anualizado requiere $11.01 de capital de trabajo.')
    c.tabla(
        'Ratios de Capital de Trabajo — Mar-26 a Jun-26', 'Ratio',
        [
            {'Ratio': 'Días CxC', 'Mar-26': 45.42, 'Abr-26': 48.76, 'May-26': 52.53, 'Jun-26': 57.99, 'Var. Jun/May': '▲ +5.46 días'},
            {'Ratio': 'Días WIP', 'Mar-26': 0, 'Abr-26': 0, 'May-26': 0, 'Jun-26': 0, 'Var. Jun/May': '→ sin cambio'},
            {'Ratio': 'Días CxP', 'Mar-26': 20.61, 'Abr-26': 20.33, 'May-26': 20.25, 'Jun-26': 22.46, 'Var. Jun/May': '▲ +2.20 días'},
            {'Ratio': 'Días Capital de Trabajo', 'Mar-26': 24.81, 'Abr-26': 28.43, 'May-26': 32.28, 'Jun-26': 35.53, 'Var. Jun/May': '▲ +3.25 días'},
            {'Ratio': 'Capital de Trabajo ($)', 'Mar-26': 2577715, 'Abr-26': 2938816, 'May-26': 3230452, 'Jun-26': 3380740, 'Var. Jun/May': '▲ +$150,288'},
            {'Ratio': 'CT por $100 de ingresos', 'Mar-26': 8.09, 'Abr-26': 9.00, 'May-26': 10.21, 'Jun-26': 11.01, 'Var. Jun/May': '▲ +$0.80'},
            {'Ratio': 'Ratio Corriente', 'Mar-26': 1.57, 'Abr-26': 1.11, 'May-26': 1.22, 'Jun-26': 1.23, 'Var. Jun/May': '▲ +0.01x'},
        ],
        ['Mar-26', 'Abr-26', 'May-26', 'Jun-26', 'Var. Jun/May'], columnas_texto=['Var. Jun/May'],
        descripcion='Metodología: Días CxC = CxC / (Ingresos del mes × 12) × 365; Días CxP = Proveedores / (Costos Directos del mes × 12) × 365; Días WIP = 0 (LCE no maneja inventario).',
    )

    c.kpi('Cartera Total (corte cobranza)', 3388555, 'Corte junio 2026')
    c.kpi('Al Corriente (Anticipada)', 2115898, '62% del portafolio')
    c.kpi('Vencida Total', 1272657, '38% del portafolio')
    c.kpi('Vencida +120 Días', 354864, '▲ 10% · excede meta máx. 5%')

    c.barra(
        'Antigüedad de Cartera — Junio 2026',
        ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días'],
        [2115898, 634964, 259546, 10425, 12858, 354864],
        chart_type='barras_verticales',
        descripcion='El 62% de la cartera está al corriente (anticipada) y el 19% adicional en el tramo 30 días — juntos, 81% del portafolio con menos de 30 días de mora. El tramo "más de 120 días" concentra $354,864 (10%), el único tramo que excede su meta de control (máximo 5%) — y de ese monto, $275,467 (78%) corresponde a un solo cliente: Transexpress. El resto ($79,397) está distribuido entre otros clientes.',
    )
    c.tabla(
        'Cumplimiento de Metas de Antigüedad (Acumulado)', 'Edad de Cartera',
        [
            {'Edad de Cartera': 'Corriente', 'Meta': '≥ 50%', 'Valor Acumulado': 2115898, 'Resultado': '62% ✓'},
            {'Edad de Cartera': 'Vencido ≤ 30 días (acum.)', 'Meta': '≥ 70%', 'Valor Acumulado': 2750862, 'Resultado': '81% ✓'},
            {'Edad de Cartera': 'Vencido ≤ 60 días (acum.)', 'Meta': '≥ 80%', 'Valor Acumulado': 3010408, 'Resultado': '89% ✓'},
            {'Edad de Cartera': 'Vencido ≤ 90 días (acum.)', 'Meta': '≥ 90%', 'Valor Acumulado': 3020833, 'Resultado': '89%'},
            {'Edad de Cartera': 'Vencido ≤ 120 días (acum.)', 'Meta': '≥ 95%', 'Valor Acumulado': 3033691, 'Resultado': '90%'},
            {'Edad de Cartera': 'Más de 120 días', 'Meta': '≤ 5%', 'Valor Acumulado': 354864, 'Resultado': '10% ✗'},
        ],
        ['Meta', 'Valor Acumulado', 'Resultado'], columnas_texto=['Meta', 'Resultado'],
        descripcion='Los tramos "≤ 90 días" (89% vs meta 90%) y "≤ 120 días" (90% vs meta 95%) quedan formalmente por debajo de su meta acumulada aunque su semaforización de origen los marca en verde. El único tramo que excede su límite de forma inequívoca es "más de 120 días" (10% vs. máximo 5%).',
    )

    c.titulo('Concentración de Cartera — Top 16 Clientes vs. Resto de la Cartera')
    c.kpi('Top 16 Clientes', 1685456, '49.75% del saldo total', ancho_columnas=2)
    c.kpi('Resto (1,267 clientes)', 1703099, '50.25% del saldo total', ancho_columnas=2)
    c.tabla(
        'Concentración de Cartera — Top 16 Clientes', 'Cliente',
        [
            {'Cliente': 'Transexpress', 'Saldo': 428176, '% sobre Total': 12.64},
            {'Cliente': 'Lion Ecommerce Logistics Limited', 'Saldo': 311759, '% sobre Total': 9.20},
            {'Cliente': 'H&M Hennes & Mauritz EC S.A.S.', 'Saldo': 211066, '% sobre Total': 6.23},
            {'Cliente': 'Superdeporte S.A.', 'Saldo': 158276, '% sobre Total': 4.67},
            {'Cliente': 'Corporación JCEVCORP Cía. Ltda.', 'Saldo': 123193, '% sobre Total': 3.64},
            {'Cliente': 'Mabel Trading S.A.', 'Saldo': 79602, '% sobre Total': 2.35},
            {'Cliente': 'Dropi S.A.S.', 'Saldo': 69816, '% sobre Total': 2.06},
            {'Cliente': 'Brodmen S.A.', 'Saldo': 42669, '% sobre Total': 1.26},
            {'Cliente': 'Cresa-Retail S.A.S.', 'Saldo': 41333, '% sobre Total': 1.22},
            {'Cliente': 'Magicnegsa S.A.', 'Saldo': 37416, '% sobre Total': 1.10},
            {'Cliente': 'Darwin Navarrete', 'Saldo': 34096, '% sobre Total': 1.01},
            {'Cliente': 'Corporación El Rosado SA', 'Saldo': 32621, '% sobre Total': 0.96},
            {'Cliente': 'Bueaño Rodríguez Karen Katherine', 'Saldo': 31722, '% sobre Total': 0.94},
            {'Cliente': 'Continental Tire Andina S.A.', 'Saldo': 28652, '% sobre Total': 0.85},
            {'Cliente': 'Mundo Deportivo Medeport S.A.', 'Saldo': 28594, '% sobre Total': 0.84},
            {'Cliente': 'Bou Company S.A.S.', 'Saldo': 26465, '% sobre Total': 0.78},
            {'Cliente': 'Resto (1,267 clientes)', 'Saldo': 1703099, '% sobre Total': 50.25},
        ],
        ['Saldo', '% sobre Total'], ancho_columnas=1,
        descripcion='La cartera está altamente atomizada fuera de los 16 principales: 1,267 clientes se reparten el 50.25% restante del saldo, con un ticket promedio de ~$1,344 por cliente. TOTAL CARTERA: $3,388,555. Nota: el total de este corte de cobranza es menor al saldo de CxC Comerciales del Balance General a junio ($4,876,663) — la diferencia ($1,488,108) podría corresponder a subcategorías no incluidas en este corte o a una fecha de corte distinta.',
    )

    c.titulo('Antigüedad de Cartera — Dos Mayores Deudores (Junio 2026)')
    c.tabla(
        'Transexpress — $428,176 (12.64% de la cartera total)', 'Tramo',
        [
            {'Tramo': 'Anticipada (corriente)', 'Saldo': 84104, '%': 20},
            {'Tramo': '30 días', 'Saldo': 66079, '%': 15},
            {'Tramo': '60 días', 'Saldo': 2526, '%': 1},
            {'Tramo': 'Más de 120 días', 'Saldo': 275467, '%': 64},
        ],
        ['Saldo', '%'], ancho_columnas=2,
        descripcion='El 64% del saldo ya superó los 120 días de mora, y ese tramo subió $25,467 vs. el corte de mayo ($250,000) — la mora no se está resolviendo, se está profundizando.',
    )
    c.tabla(
        'Lion Ecommerce Logistics Limited — $311,759 (9.20% de la cartera total)', 'Tramo',
        [
            {'Tramo': '30 días', 'Saldo': 153045, '%': 49},
            {'Tramo': '60 días', 'Saldo': 158714, '%': 51},
        ],
        ['Saldo', '%'], ancho_columnas=2,
        descripcion='A diferencia de Transexpress, el 100% del saldo de este cliente está vencido (nada anticipado/corriente), pero concentrado en mora reciente (30-60 días) — retraso generalizado, no incobrabilidad de largo plazo.',
    )
    c.texto('Son dos problemas de cartera distintos que requieren gestión diferente: Transexpress es mora crónica y de largo plazo (64% vencido +120 días, en aumento) — requiere renegociación de condiciones o vía legal. Lion Ecommerce Logistics es mora reciente pero total (100% del saldo vencido) — requiere gestión de cobranza inmediata antes de que ese saldo escale a los tramos de mayor antigüedad.')

    c.titulo('Anexo — Transexpress: Evolución del Saldo (Ene–Jun 2026)')
    c.kpi('Saldo Promedio Ene–May', 407233, 'Rango $387K–$451K')
    c.kpi('Saldo Junio (corte)', 428176, '12.64% de la cartera total')
    c.kpi('Vencido +120 días (Jun)', 275467, '▲ +$25,467 vs mayo ($250,000)')
    c.kpi('Recuperación estimada (semanas)', 6, '~6 sem. — a ritmo de $40K/semana, solo tramo vencido')
    c.barra(
        'Transexpress — Evolución del Saldo (Ene–Jun 2026)', meses6,
        [408420, 390067, 400157, 386521, 451000, 428176],
        chart_type='barras_verticales',
        descripcion='El saldo de Transexpress se mantiene en un rango estrecho ($386K–$451K) durante todo el semestre, sin una tendencia clara de reducción: mayo marcó el máximo ($451K) y junio retrocede a $428K. Sin embargo, la calidad de esa cartera empeoró: el tramo vencido +120 días creció de $250,000 a $275,467. Nota: el original superpone marcadores del monto vencido +120 días sobre las barras del saldo total — acá se omiten (queda solo el saldo total por mes), el dato vencido ya está en el KPI y el texto de arriba.',
    )

    c.titulo('Lectura Ejecutiva — Cartera')
    c.texto('"Transexpress y Lion Ecommerce Logistics concentran juntos el 21.84% de la cartera total y requieren gestión de cobranza diferenciada: renegociación para Transexpress (mora crónica), cobranza inmediata para Lion Ecommerce (mora reciente pero total)."')


def poblar_cartera(c):
    """Solo la sección 6 (Cartera) del informe original — versión standalone de la 2da mitad de
    `poblar_capital_cartera`, usada cuando el dashboard debe quedar SOLO con Cartera (sin Capital
    de Trabajo), ver `limpiar_informe_lce_solo_cartera.py`."""
    meses6 = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']

    c.kpi('Cartera Total (corte cobranza)', 3388555, 'Corte junio 2026')
    c.kpi('Al Corriente (Anticipada)', 2115898, '62% del portafolio')
    c.kpi('Vencida Total', 1272657, '38% del portafolio')
    c.kpi('Vencida +120 Días', 354864, '▲ 10% · excede meta máx. 5%')

    c.barra(
        'Antigüedad de Cartera — Junio 2026',
        ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días'],
        [2115898, 634964, 259546, 10425, 12858, 354864],
        chart_type='barras_verticales',
        descripcion='El 62% de la cartera está al corriente (anticipada) y el 19% adicional en el tramo 30 días — juntos, 81% del portafolio con menos de 30 días de mora. El tramo "más de 120 días" concentra $354,864 (10%), el único tramo que excede su meta de control (máximo 5%) — y de ese monto, $275,467 (78%) corresponde a un solo cliente: Transexpress. El resto ($79,397) está distribuido entre otros clientes. Nota: el editor de dashboards ordena las barras por magnitud (de mayor a menor), no por antigüedad — no es el orden natural Anticipada→30→60→90→120→+120 del informe original.',
    )
    c.tabla(
        'Cumplimiento de Metas de Antigüedad (Acumulado)', 'Edad de Cartera',
        [
            {'Edad de Cartera': 'Corriente', 'Meta': '≥ 50%', 'Valor Acumulado': 2115898, 'Resultado': '62% ✓'},
            {'Edad de Cartera': 'Vencido ≤ 30 días (acum.)', 'Meta': '≥ 70%', 'Valor Acumulado': 2750862, 'Resultado': '81% ✓'},
            {'Edad de Cartera': 'Vencido ≤ 60 días (acum.)', 'Meta': '≥ 80%', 'Valor Acumulado': 3010408, 'Resultado': '89% ✓'},
            {'Edad de Cartera': 'Vencido ≤ 90 días (acum.)', 'Meta': '≥ 90%', 'Valor Acumulado': 3020833, 'Resultado': '89%'},
            {'Edad de Cartera': 'Vencido ≤ 120 días (acum.)', 'Meta': '≥ 95%', 'Valor Acumulado': 3033691, 'Resultado': '90%'},
            {'Edad de Cartera': 'Más de 120 días', 'Meta': '≤ 5%', 'Valor Acumulado': 354864, 'Resultado': '10% ✗'},
        ],
        ['Meta', 'Valor Acumulado', 'Resultado'], columnas_texto=['Meta', 'Resultado'],
        descripcion='Los tramos "≤ 90 días" (89% vs meta 90%) y "≤ 120 días" (90% vs meta 95%) quedan formalmente por debajo de su meta acumulada aunque su semaforización de origen los marca en verde. El único tramo que excede su límite de forma inequívoca es "más de 120 días" (10% vs. máximo 5%).',
    )

    c.titulo('Concentración de Cartera — Top 16 Clientes vs. Resto de la Cartera')
    c.kpi('Top 16 Clientes', 1685456, '49.75% del saldo total', ancho_columnas=2)
    c.kpi('Resto (1,267 clientes)', 1703099, '50.25% del saldo total', ancho_columnas=2)
    c.tabla(
        'Concentración de Cartera — Top 16 Clientes', 'Cliente',
        [
            {'Cliente': 'Transexpress', 'Saldo': 428176, '% sobre Total': 12.64},
            {'Cliente': 'Lion Ecommerce Logistics Limited', 'Saldo': 311759, '% sobre Total': 9.20},
            {'Cliente': 'H&M Hennes & Mauritz EC S.A.S.', 'Saldo': 211066, '% sobre Total': 6.23},
            {'Cliente': 'Superdeporte S.A.', 'Saldo': 158276, '% sobre Total': 4.67},
            {'Cliente': 'Corporación JCEVCORP Cía. Ltda.', 'Saldo': 123193, '% sobre Total': 3.64},
            {'Cliente': 'Mabel Trading S.A.', 'Saldo': 79602, '% sobre Total': 2.35},
            {'Cliente': 'Dropi S.A.S.', 'Saldo': 69816, '% sobre Total': 2.06},
            {'Cliente': 'Brodmen S.A.', 'Saldo': 42669, '% sobre Total': 1.26},
            {'Cliente': 'Cresa-Retail S.A.S.', 'Saldo': 41333, '% sobre Total': 1.22},
            {'Cliente': 'Magicnegsa S.A.', 'Saldo': 37416, '% sobre Total': 1.10},
            {'Cliente': 'Darwin Navarrete', 'Saldo': 34096, '% sobre Total': 1.01},
            {'Cliente': 'Corporación El Rosado SA', 'Saldo': 32621, '% sobre Total': 0.96},
            {'Cliente': 'Bueaño Rodríguez Karen Katherine', 'Saldo': 31722, '% sobre Total': 0.94},
            {'Cliente': 'Continental Tire Andina S.A.', 'Saldo': 28652, '% sobre Total': 0.85},
            {'Cliente': 'Mundo Deportivo Medeport S.A.', 'Saldo': 28594, '% sobre Total': 0.84},
            {'Cliente': 'Bou Company S.A.S.', 'Saldo': 26465, '% sobre Total': 0.78},
            {'Cliente': 'Resto (1,267 clientes)', 'Saldo': 1703099, '% sobre Total': 50.25},
        ],
        ['Saldo', '% sobre Total'], ancho_columnas=1,
        descripcion='La cartera está altamente atomizada fuera de los 16 principales: 1,267 clientes se reparten el 50.25% restante del saldo, con un ticket promedio de ~$1,344 por cliente. TOTAL CARTERA: $3,388,555. Nota: el total de este corte de cobranza es menor al saldo de CxC Comerciales del Balance General a junio ($4,876,663) — la diferencia ($1,488,108) podría corresponder a subcategorías no incluidas en este corte o a una fecha de corte distinta.',
    )

    c.titulo('Antigüedad de Cartera — Dos Mayores Deudores (Junio 2026)')
    c.tabla(
        'Transexpress — $428,176 (12.64% de la cartera total)', 'Tramo',
        [
            {'Tramo': 'Anticipada (corriente)', 'Saldo': 84104, '%': 20},
            {'Tramo': '30 días', 'Saldo': 66079, '%': 15},
            {'Tramo': '60 días', 'Saldo': 2526, '%': 1},
            {'Tramo': 'Más de 120 días', 'Saldo': 275467, '%': 64},
        ],
        ['Saldo', '%'], ancho_columnas=2,
        descripcion='El 64% del saldo ya superó los 120 días de mora, y ese tramo subió $25,467 vs. el corte de mayo ($250,000) — la mora no se está resolviendo, se está profundizando.',
    )
    c.tabla(
        'Lion Ecommerce Logistics Limited — $311,759 (9.20% de la cartera total)', 'Tramo',
        [
            {'Tramo': '30 días', 'Saldo': 153045, '%': 49},
            {'Tramo': '60 días', 'Saldo': 158714, '%': 51},
        ],
        ['Saldo', '%'], ancho_columnas=2,
        descripcion='A diferencia de Transexpress, el 100% del saldo de este cliente está vencido (nada anticipado/corriente), pero concentrado en mora reciente (30-60 días) — retraso generalizado, no incobrabilidad de largo plazo.',
    )
    c.texto('Son dos problemas de cartera distintos que requieren gestión diferente: Transexpress es mora crónica y de largo plazo (64% vencido +120 días, en aumento) — requiere renegociación de condiciones o vía legal. Lion Ecommerce Logistics es mora reciente pero total (100% del saldo vencido) — requiere gestión de cobranza inmediata antes de que ese saldo escale a los tramos de mayor antigüedad.')

    c.titulo('Anexo — Transexpress: Evolución del Saldo (Ene–Jun 2026)')
    c.kpi('Saldo Promedio Ene–May', 407233, 'Rango $387K–$451K')
    c.kpi('Saldo Junio (corte)', 428176, '12.64% de la cartera total')
    c.kpi('Vencido +120 días (Jun)', 275467, '▲ +$25,467 vs mayo ($250,000)')
    c.kpi('Recuperación estimada (semanas)', 6, '~6 sem. — a ritmo de $40K/semana, solo tramo vencido')
    c.barra(
        'Transexpress — Evolución del Saldo (Ene–Jun 2026)', meses6,
        [408420, 390067, 400157, 386521, 451000, 428176],
        chart_type='barras_verticales',
        descripcion='El saldo de Transexpress se mantiene en un rango estrecho ($386K–$451K) durante todo el semestre, sin una tendencia clara de reducción: mayo marcó el máximo ($451K) y junio retrocede a $428K. Sin embargo, la calidad de esa cartera empeoró: el tramo vencido +120 días creció de $250,000 a $275,467. Nota: el original superpone marcadores del monto vencido +120 días sobre las barras del saldo total — acá se omiten (queda solo el saldo total por mes). Nota: el editor ordena las barras por magnitud, no cronológicamente — no queda Ene→Jun de izquierda a derecha.',
    )

    c.titulo('Lectura Ejecutiva — Cartera')
    c.texto('"Transexpress y Lion Ecommerce Logistics concentran juntos el 21.84% de la cartera total y requieren gestión de cobranza diferenciada: renegociación para Transexpress (mora crónica), cobranza inmediata para Lion Ecommerce (mora reciente pero total)."')


# ══════════════════════════════════════════════════════════════════════════════════════════════
class Command(BaseCommand):
    help = (
        'Puebla (una sola vez) el dashboard "Administracion" con la estructura del informe '
        'financiero LCE junio 2026, en 5 pestañas. Ver el docstring del módulo para el detalle '
        'de aproximaciones y el alcance de "Fase 1" (datos fijos, no conectados a un archivo).'
    )

    def handle(self, *args, **options):
        raiz = dashboards_service._obtener_dashboard_o_error(DASHBOARD_RAIZ)
        if raiz.parent_id:
            raise SystemExit(f'"{DASHBOARD_RAIZ}" ya es una pestaña de otra familia, no la raíz.')

        pestanas_existentes = list(raiz.pestanas.order_by('orden').values_list('name', flat=True))
        nombres_nuevas = [
            'Rentabilidad', 'Balance General', 'Caja, Deuda y Situación de Caja', 'Capital de Trabajo y Cartera',
        ]
        faltantes = [n for n in nombres_nuevas if n not in pestanas_existentes]
        if pestanas_existentes and len(pestanas_existentes) + 1 + len(faltantes) > 5:
            raise SystemExit(
                f'"{DASHBOARD_RAIZ}" ya tiene pestañas que no son las esperadas de este script '
                f'({pestanas_existentes}) — revisar a mano antes de correr este comando.'
            )

        ids = {'Resumen Ejecutivo': DASHBOARD_RAIZ}
        for nombre in nombres_nuevas:
            existente = raiz.pestanas.filter(name=nombre).first()
            if existente:
                ids[nombre] = existente.dashboard_id
                self.stdout.write(f'Pestaña "{nombre}" ya existía ({existente.dashboard_id}), la reuso.')
            else:
                pestana = dashboards_service.crear_pestana(DASHBOARD_RAIZ, nombre=nombre)
                ids[nombre] = pestana.dashboard_id
                self.stdout.write(self.style.SUCCESS(f'Pestaña "{nombre}" creada ({pestana.dashboard_id}).'))

        poblar_resumen_ejecutivo(ConstructorDashboard(ids['Resumen Ejecutivo']))
        self.stdout.write(self.style.SUCCESS('Resumen Ejecutivo poblado.'))

        poblar_rentabilidad(ConstructorDashboard(ids['Rentabilidad']))
        self.stdout.write(self.style.SUCCESS('Rentabilidad poblado.'))

        poblar_balance_general(ConstructorDashboard(ids['Balance General']))
        self.stdout.write(self.style.SUCCESS('Balance General poblado.'))

        poblar_caja_deuda(ConstructorDashboard(ids['Caja, Deuda y Situación de Caja']))
        self.stdout.write(self.style.SUCCESS('Caja, Deuda y Situación de Caja poblado.'))

        poblar_capital_cartera(ConstructorDashboard(ids['Capital de Trabajo y Cartera']))
        self.stdout.write(self.style.SUCCESS('Capital de Trabajo y Cartera poblado.'))

        self.stdout.write(self.style.SUCCESS('Listo. 5 pestañas pobladas con la estructura del informe LCE junio 2026 (Fase 1, datos fijos).'))
