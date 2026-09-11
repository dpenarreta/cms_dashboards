"""Reconstruye el dashboard "Administracion" (Cartera) con datos REALES calculados desde un
Excel de cartera crudo (mismo formato que usa "Seguimiento de Cartera": una fila por documento,
columnas `Cliente`, `Saldo`, `VENCE`) — a diferencia de `poblar_informe_lce_junio2026.py` (Fase 1,
cifras fijas transcritas del PDF), acá el KPI/gráfico/tabla se calcula con pandas a partir del
archivo real, reproduciendo la MISMA lógica de negocio que el informe original (tramos de
antigüedad, cumplimiento de metas, top 16 clientes + resto, dos mayores deudores).

Reusa `ConstructorDashboard` (los mismos helpers `.kpi()`/`.barra()`/`.tabla()`/`.titulo()`/
`.texto()` de `poblar_informe_lce_junio2026.py`, que a su vez ya reusan
`generic_charts.py`/`dashboard_layout.py`) — la única diferencia real es que los NÚMEROS que se le
pasan a esos helpers salen de `df.groupby(...)` en vez de estar escritos a mano.

Limitaciones conocidas (el archivo es un corte de UN solo momento, sin histórico mensual):
- No hay comparación "vs mes anterior" en los KPIs (no existe un período previo en este archivo).
- Se cae el "Anexo — Evolución del Saldo (Ene-Jun)" del cliente principal: requiere una serie
  histórica mensual que este archivo no trae. Si se necesita, habría que guardar el resultado de
  cada corte mensual en algún lado para poder graficar la evolución más adelante.
- El "Cumplimiento de Metas" usa los mismos umbrales fijos del informe original (≥50%, ≥70%, etc.)
  — son una política de negocio, no algo que se pueda derivar del archivo.
- Sigue vigente la limitación ya señalada de `generic_charts.py`: las categorías (tramos de
  antigüedad, clientes) se ordenan por magnitud, no en el orden lógico del informe.
"""

import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from .poblar_informe_lce_junio2026 import DASHBOARD_RAIZ, ConstructorDashboard

TRAMOS_EXPLICITOS = ['ANTICIPADA', '30 DIAS', '60 DIAS', '90 DIAS', '120 DIAS']
ETIQUETA_TRAMO = {
    'ANTICIPADA': 'Anticipada', '30 DIAS': '30 días', '60 DIAS': '60 días',
    '90 DIAS': '90 días', '120 DIAS': '120 días',
}
ORDEN_TRAMOS = ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días']

METAS_CUMPLIMIENTO = [
    ('Corriente', ['Anticipada'], 50, '≥'),
    ('Vencido ≤ 30 días (acum.)', ['Anticipada', '30 días'], 70, '≥'),
    ('Vencido ≤ 60 días (acum.)', ['Anticipada', '30 días', '60 días'], 80, '≥'),
    ('Vencido ≤ 90 días (acum.)', ['Anticipada', '30 días', '60 días', '90 días'], 90, '≥'),
    ('Vencido ≤ 120 días (acum.)', ['Anticipada', '30 días', '60 días', '90 días', '120 días'], 95, '≥'),
    ('Más de 120 días', ['+120 días'], 5, '≤'),
]


def _tramo(vence):
    vence = str(vence).strip().upper()
    return ETIQUETA_TRAMO.get(vence, '+120 días') if vence in TRAMOS_EXPLICITOS else '+120 días'


class Command(BaseCommand):
    help = 'Reconstruye "Administracion" (Cartera) con datos reales calculados desde un Excel de cartera crudo.'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', required=True, help='Ruta al Excel de cartera (mismo formato que "Seguimiento de Cartera").')

    def handle(self, *args, **options):
        ruta = options['archivo']
        try:
            df = pd.read_excel(ruta)
        except Exception as exc:
            raise CommandError(f'No se pudo leer "{ruta}": {exc}')

        for col in ('Cliente', 'Saldo', 'VENCE'):
            if col not in df.columns:
                raise CommandError(f'El archivo no tiene la columna "{col}".')

        df['Saldo'] = pd.to_numeric(df['Saldo'], errors='coerce').fillna(0.0)
        df['Tramo'] = df['VENCE'].apply(_tramo)

        total = float(df['Saldo'].sum())
        por_tramo = df.groupby('Tramo')['Saldo'].sum().reindex(ORDEN_TRAMOS, fill_value=0.0)
        anticipada = float(por_tramo['Anticipada'])
        vencida_total = total - anticipada
        vencida_120 = float(por_tramo['+120 días'])

        por_cliente = df.groupby('Cliente')['Saldo'].sum().sort_values(ascending=False)
        top16 = por_cliente.head(16)
        resto_suma = float(por_cliente.iloc[16:].sum())
        resto_n = len(por_cliente) - len(top16)

        c = ConstructorDashboard(DASHBOARD_RAIZ)

        c.titulo(f'Cartera — Datos reales cargados desde "{ruta.split(chr(92))[-1]}"')
        c.texto(f'Corte con {len(df)} documentos y {df["Cliente"].nunique()} clientes. Sin período anterior para comparar en este archivo (corte de un solo momento) — no hay "vs mes anterior" en los KPIs de abajo.')

        c.kpi('Cartera Total (corte actual)', round(total, 2), f'{len(df)} documentos')
        c.kpi('Al Corriente (Anticipada)', round(anticipada, 2), f'{(anticipada / total * 100 if total else 0):.0f}% del portafolio')
        c.kpi('Vencida Total', round(vencida_total, 2), f'{(vencida_total / total * 100 if total else 0):.0f}% del portafolio')
        c.kpi('Vencida +120 Días', round(vencida_120, 2), f'{(vencida_120 / total * 100 if total else 0):.0f}% del portafolio')

        c.barra(
            'Antigüedad de Cartera (datos reales)', ORDEN_TRAMOS, [round(float(por_tramo[t]), 2) for t in ORDEN_TRAMOS],
            chart_type='barras_verticales',
            descripcion='Calculado en vivo desde la columna VENCE del archivo cargado (Anticipada/30/60/90/120 días explícitos; todo lo demás — 150 a +360 días — se agrupa en "+120 días"). Nota: el editor ordena las barras por magnitud, no por antigüedad.',
        )

        filas_metas = []
        for etiqueta, tramos_incluidos, umbral, comparador in METAS_CUMPLIMIENTO:
            valor_acum = sum(float(por_tramo[t]) for t in tramos_incluidos)
            pct = (valor_acum / total * 100) if total else 0.0
            cumple = pct >= umbral if comparador == '≥' else pct <= umbral
            filas_metas.append({
                'Edad de Cartera': etiqueta, 'Meta': f'{comparador} {umbral}%',
                'Valor Acumulado': round(valor_acum, 2), 'Resultado': f'{pct:.0f}% {"✓" if cumple else "✗"}',
            })
        c.tabla(
            'Cumplimiento de Metas de Antigüedad (Acumulado) — datos reales', 'Edad de Cartera', filas_metas,
            ['Meta', 'Valor Acumulado', 'Resultado'], columnas_texto=['Meta', 'Resultado'],
            descripcion='Metas fijas del informe original (política de negocio, no derivada del archivo): Corriente ≥50%, acumulado ≤30d ≥70%, ≤60d ≥80%, ≤90d ≥90%, ≤120d ≥95%, +120d ≤5%.',
        )

        c.titulo('Concentración de Cartera — Top 16 Clientes vs. Resto (datos reales)')
        c.kpi('Top 16 Clientes', round(float(top16.sum()), 2), f'{(top16.sum() / total * 100 if total else 0):.2f}% del saldo total', ancho_columnas=2)
        c.kpi(f'Resto ({resto_n} clientes)', round(resto_suma, 2), f'{(resto_suma / total * 100 if total else 0):.2f}% del saldo total', ancho_columnas=2)

        filas_top16 = []
        acumulado = 0.0
        for cliente, saldo in top16.items():
            pct = (float(saldo) / total * 100) if total else 0.0
            acumulado += pct
            filas_top16.append({'Cliente': str(cliente), 'Saldo': round(float(saldo), 2), '% sobre Total': round(pct, 2), '% Acumulado': round(acumulado, 2)})
        filas_top16.append({
            'Cliente': f'Resto ({resto_n} clientes)', 'Saldo': round(resto_suma, 2),
            '% sobre Total': round((resto_suma / total * 100) if total else 0.0, 2), '% Acumulado': 100.0,
        })
        c.tabla(
            'Concentración de Cartera — Top 16 Clientes (datos reales)', 'Cliente', filas_top16,
            ['Saldo', '% sobre Total', '% Acumulado'], ancho_columnas=1,
            descripcion=f'Cartera total: {total:,.2f}. Calculado en vivo agrupando por Cliente y sumando Saldo.',
        )

        c.titulo('Antigüedad de Cartera — Dos Mayores Deudores (datos reales)')
        dos_mayores = por_cliente.head(2)
        for cliente, saldo_cliente in dos_mayores.items():
            filas_cliente = df[df['Cliente'] == cliente].groupby('Tramo')['Saldo'].sum().reindex(ORDEN_TRAMOS, fill_value=0.0)
            filas_cliente = filas_cliente[filas_cliente > 0]
            pct_cliente = (float(saldo_cliente) / total * 100) if total else 0.0
            c.tabla(
                f'{cliente} — {saldo_cliente:,.2f} ({pct_cliente:.2f}% de la cartera total)', 'Tramo',
                [
                    {'Tramo': t, 'Saldo': round(float(v), 2), '%': round((float(v) / saldo_cliente * 100) if saldo_cliente else 0.0, 2)}
                    for t, v in filas_cliente.items()
                ],
                ['Saldo', '%'], ancho_columnas=2,
            )
        nombres = ' y '.join(str(c_) for c_ in dos_mayores.index)
        pct_combinado = (float(dos_mayores.sum()) / total * 100) if total else 0.0
        c.texto(f'Entre {nombres} concentran {dos_mayores.sum():,.2f} ({pct_combinado:.2f}%) de la cartera total.')

        c.titulo('Lectura Ejecutiva — Cartera (datos reales)')
        c.texto(f'"{nombres} concentran juntos el {pct_combinado:.2f}% de la cartera total — priorizar su gestión de cobranza."')

        self.stdout.write(self.style.SUCCESS(
            f'"{DASHBOARD_RAIZ}" reconstruido con datos reales de "{ruta}" '
            f'(cartera total {total:,.2f}, {len(df)} documentos, {df["Cliente"].nunique()} clientes).'
        ))
