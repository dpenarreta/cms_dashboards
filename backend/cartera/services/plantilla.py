"""Plantilla fija de dashboard: 15 posiciones (4 KPI, 6 gráficos, 5 tablas) que todo dashboard
nuevo trae desde su creación (`sembrar_plantilla`, llamado por `services.dashboards.crear_dashboard`),
con datos ficticios mientras no se haya cargado ningún archivo. Al cargar un archivo, se propone
un mapeo automático de columnas a esas mismas 15 posiciones (`sugerir_mapeo`) que el usuario
puede ajustar antes de confirmarlo (`aplicar_mapeo`) — reemplaza al viejo flujo de "recomendar
gráficas sueltas" (`AnalizarColumnasView`/`RecomendarGraficasView`/`AgregarGraficaView`, que se
dejan intactos pero sin consumidor en el frontend nuevo).

De esas 5 tablas, las últimas dos (Tabla 4 y Tabla 5) son especiales: en vez de mostrar el detalle
del último archivo cargado (como Tabla 1/2/3), el frontend (`TablaHistoricaAutomatica.jsx`) las
intercepta por `component_id` para comparar en vivo todas las cargas históricas del dashboard —
por eso van al final de `PLANTILLA_SLOTS` ("al final del dashboard") y llevan una etiqueta fija
"Histórica" junto a su título. Acá, en el backend, no se distinguen de Tabla 1/2/3: tienen el mismo
`calculo='tabla'` y el mismo mapeo columna_id/columnas_valor, así que su contenido ficticio o real
sigue sirviendo de resguardo si el dashboard todavía no tiene ninguna carga histórica.

Cada posición conserva su identidad visual (título, ícono/color de los KPI) sin importar qué
columna la alimente; solo cambian los datos. Una posición sin columnas adecuadas en el archivo
conserva su dato ficticio en vez de bloquear el resto del mapeo — un archivo de cualquier área
(RRHH, TI, inventario...) rara vez tiene las 13 combinaciones de columnas que la plantilla ilustra.
"""

from apps.audit.models import AuditEvent
from apps.audit.services import log_event

from ..models import DashboardComponent
from . import dashboard_layout, generic_charts

KPI_ANCHO, KPI_ALTO = 3, 180
GRAFICO_MEDIO_ANCHO, GRAFICO_ALTO = 6, 380
GRAFICO_COMPLETO_ANCHO = 12
GRAFICO_TERCIO_ANCHO, GRAFICO_TERCIO_ALTO = 4, 340
TABLA_COMPLETA_ALTO = 380
TABLA_MEDIA_ANCHO, TABLA_MEDIA_ALTO = 6, 340

# `calculo` identifica, para cada posición, qué función de `generic_charts` la calcula y qué
# columnas necesita — ver `_calcular_contenido_slot`. Los `component_id` son fijos (no derivados
# de un título): aplicar el mapeo o restablecer la plantilla siempre actualiza los mismos 13
# componentes, nunca los duplica.
#
# El ORDEN de esta lista es también el `order` con el que cada posición se siembra por defecto
# (`_escribir_plantilla`), y por lo tanto la secuencia visual real del grid (`EditableGrid.jsx`
# acomoda por `order` con flex-wrap de 12 columnas — `row` no se usa para renderizar). Se pensó
# para seguir el patrón de lectura en "Z": franja superior de KPIs (barrido horizontal inicial),
# seguida de inmediato por el único gráfico de ancho completo (grafico-3, "área apilada") como
# ancla visual del barrido diagonal — antes de que dos gráficos de ancho medio le resten
# protagonismo — y recién después el resto de gráficos de apoyo, cerrando con las tablas de
# detalle (barrido horizontal final, terminando en la tabla más específica abajo a la derecha).
PLANTILLA_SLOTS = [
    {'id': 'kpi-1', 'tipo': DashboardComponent.Tipo.KPI, 'chart_type': '', 'ancho': KPI_ANCHO, 'alto': KPI_ALTO,
     'titulo': 'KPI 1', 'calculo': 'kpi', 'color_defecto': '#2a78d6', 'config_fijo': {'icono': 'persona'}},
    {'id': 'kpi-2', 'tipo': DashboardComponent.Tipo.KPI, 'chart_type': '', 'ancho': KPI_ANCHO, 'alto': KPI_ALTO,
     'titulo': 'KPI 2', 'calculo': 'kpi', 'color_defecto': '#1baf7a', 'config_fijo': {'icono': 'dolar'}},
    {'id': 'kpi-3', 'tipo': DashboardComponent.Tipo.KPI, 'chart_type': '', 'ancho': KPI_ANCHO, 'alto': KPI_ALTO,
     'titulo': 'KPI 3', 'calculo': 'kpi', 'color_defecto': '#8b5cf6', 'config_fijo': {'icono': 'carrito'}},
    {'id': 'kpi-4', 'tipo': DashboardComponent.Tipo.KPI, 'chart_type': '', 'ancho': KPI_ANCHO, 'alto': KPI_ALTO,
     'titulo': 'KPI 4', 'calculo': 'kpi', 'color_defecto': '#eda100', 'config_fijo': {'icono': 'grafico'}},
    {'id': 'grafico-3', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'area_apilada',
     'ancho': GRAFICO_COMPLETO_ANCHO, 'alto': GRAFICO_ALTO, 'titulo': 'Gráfico 3', 'calculo': 'multiserie', 'config_fijo': {}},
    {'id': 'grafico-1', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'barras_verticales',
     'ancho': GRAFICO_MEDIO_ANCHO, 'alto': GRAFICO_ALTO, 'titulo': 'Gráfico 1', 'calculo': 'chart', 'config_fijo': {}},
    {'id': 'grafico-2', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'lineas_multiples',
     'ancho': GRAFICO_MEDIO_ANCHO, 'alto': GRAFICO_ALTO, 'titulo': 'Gráfico 2', 'calculo': 'multivalor', 'config_fijo': {}},
    {'id': 'grafico-4', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'dona',
     'ancho': GRAFICO_TERCIO_ANCHO, 'alto': GRAFICO_TERCIO_ALTO, 'titulo': 'Gráfico 4', 'calculo': 'chart',
     'config_fijo': {'mostrar_total': True}},
    {'id': 'grafico-5', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'pastel',
     'ancho': GRAFICO_TERCIO_ANCHO, 'alto': GRAFICO_TERCIO_ALTO, 'titulo': 'Gráfico 5', 'calculo': 'chart', 'config_fijo': {}},
    {'id': 'grafico-6', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'dispersion',
     'ancho': GRAFICO_TERCIO_ANCHO, 'alto': GRAFICO_TERCIO_ALTO, 'titulo': 'Gráfico 6', 'calculo': 'dispersion', 'config_fijo': {}},
    {'id': 'tabla-1', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'tabla',
     'ancho': GRAFICO_COMPLETO_ANCHO, 'alto': TABLA_COMPLETA_ALTO, 'titulo': 'Tabla 1', 'calculo': 'tabla', 'config_fijo': {}},
    {'id': 'tabla-2', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'tabla',
     'ancho': TABLA_MEDIA_ANCHO, 'alto': TABLA_MEDIA_ALTO, 'titulo': 'Tabla 2', 'calculo': 'tabla', 'config_fijo': {}},
    {'id': 'tabla-3', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'tabla',
     'ancho': TABLA_MEDIA_ANCHO, 'alto': TABLA_MEDIA_ALTO, 'titulo': 'Tabla 3', 'calculo': 'tabla', 'config_fijo': {}},
    {'id': 'tabla-4', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'tabla',
     'ancho': TABLA_MEDIA_ANCHO, 'alto': TABLA_MEDIA_ALTO, 'titulo': 'Tabla 4', 'calculo': 'tabla', 'config_fijo': {}},
    {'id': 'tabla-5', 'tipo': DashboardComponent.Tipo.CHART, 'chart_type': 'tabla',
     'ancho': TABLA_MEDIA_ANCHO, 'alto': TABLA_MEDIA_ALTO, 'titulo': 'Tabla 5', 'calculo': 'tabla', 'config_fijo': {}},
]

_SLOTS_POR_ID = {slot['id']: slot for slot in PLANTILLA_SLOTS}

# `dashboard_id` reservado (nunca corresponde a un `Dashboard` real, ver
# `services/dashboards.py::_generar_dashboard_id_unico`) para la plantilla base personalizable
# desde "Configuración → Plantilla base": usa exactamente `DashboardLayout`/`DashboardComponent`
# como cualquier dashboard (sin modelo/migración aparte), sembrada la primera vez con
# `PLANTILLA_SLOTS` — ver `slots_efectivos`/`sembrar_plantilla_desde_base`.
DASHBOARD_ID_PLANTILLA_BASE = 'plantilla-base-sistema'

# Tipos de visualización entre los que se puede cambiar una posición sin cambiar su `calculo`
# (mismos datos calculados, `{categorias, valores}` o `{categorias, series}` — ver
# `_calcular_contenido_slot`), agrupados por lo que el archivo real termina alimentando. KPI,
# dispersión y tabla no aparecen: su `calculo` solo puede dibujarse de una forma.
#
# `pastel`/`dona` también son compatibles con `multivalor`/`multiserie` (2+ columnas de valor):
# el contenido calculado sigue siendo `{categorias, series}` igual que para el resto de tipos de
# ese `calculo` (este módulo no sabe ni le importa cómo se va a dibujar) — es el frontend
# (`GenericChartRenderer`) el que colapsa las series en una sola porción por categoría cuando el
# tipo elegido es circular, así el usuario no tiene que rehacer el mapeo a una sola columna.
TIPOS_COMPATIBLES = {
    'chart': ('barras_verticales', 'barras_horizontales', 'lineas', 'pastel', 'dona'),
    'multivalor': ('barras_agrupadas', 'barras_apiladas', 'area_apilada', 'lineas_multiples', 'pastel', 'dona'),
    'multiserie': ('barras_agrupadas', 'barras_apiladas', 'area_apilada', 'lineas_multiples', 'pastel', 'dona'),
}


def _chart_type_elegido(slot, propuesta):
    """El `chart_type` que el usuario eligió para esta posición, si es compatible con su
    `calculo` — cualquier otro caso (no eligió nada, o el valor no aplica a este `calculo`) usa el
    tipo por defecto de la posición."""
    compatibles = TIPOS_COMPATIBLES.get(slot['calculo'])
    elegido = (propuesta or {}).get('chart_type')
    if compatibles and elegido in compatibles:
        return elegido
    return slot['chart_type']


def datos_ficticios():
    """Contenido de ejemplo para cada posición — la misma información que antes vivía en
    `DashboardPlaceholderTemplate.jsx` (retirado), ahora la única fuente de verdad porque los 13
    componentes se guardan de verdad desde la creación del dashboard."""
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
    categorias_producto = ['Electrónica', 'Hogar', 'Moda', 'Deportes', 'Belleza']
    valores_producto = [245000, 180000, 135000, 98000, 87000]
    descripcion_kpi = 'Dato de ejemplo — se reemplaza al cargar un archivo.'

    return {
        'kpi-1': {
            'titulo': 'KPI 1', 'descripcion': descripcion_kpi, 'valor': 12458, 'formato': 'numero',
            'tendencia': {'valor': 8.5, 'texto': 'vs. mes anterior'},
        },
        'kpi-2': {
            'titulo': 'KPI 2', 'descripcion': descripcion_kpi, 'valor': 1245300, 'formato': 'moneda',
            'tendencia': {'valor': 12.3, 'texto': 'vs. mes anterior'},
        },
        'kpi-3': {
            'titulo': 'KPI 3', 'descripcion': descripcion_kpi, 'valor': 3682, 'formato': 'numero',
            'tendencia': {'valor': 5.7, 'texto': 'vs. mes anterior'},
        },
        'kpi-4': {
            'titulo': 'KPI 4', 'descripcion': descripcion_kpi, 'valor': 78.6, 'formato': 'porcentaje',
            'tendencia': {'valor': 4.2, 'texto': 'vs. mes anterior'},
        },
        'grafico-1': {
            'titulo': 'Gráfico 1', 'descripcion': 'Ejemplo de ventas mensuales.',
            'categorias': meses, 'valores': [120000, 135000, 150000, 170000, 190000, 220000],
        },
        'grafico-2': {
            'titulo': 'Gráfico 2', 'descripcion': 'Ejemplo: comparación de dos métricas mes a mes.',
            'categorias': meses,
            'series': [
                {'nombre': 'Ingresos (USD)', 'valores': [110000, 130000, 160000, 180000, 210000, 240000]},
                {'nombre': 'Gastos (USD)', 'valores': [70000, 80000, 90000, 110000, 120000, 140000]},
            ],
        },
        'grafico-3': {
            'titulo': 'Gráfico 3', 'descripcion': 'Ejemplo: ventas por producto a lo largo del tiempo.',
            'categorias': meses,
            'series': [
                {'nombre': 'Producto A', 'valores': [60000, 65000, 70000, 75000, 80000, 100000]},
                {'nombre': 'Producto B', 'valores': [50000, 55000, 60000, 60000, 65000, 80000]},
                {'nombre': 'Producto C', 'valores': [40000, 45000, 50000, 45000, 55000, 60000]},
            ],
        },
        'grafico-4': {
            'titulo': 'Gráfico 4', 'descripcion': 'Ejemplo: distribución por categoría.',
            'categorias': categorias_producto, 'valores': valores_producto,
        },
        'grafico-5': {
            'titulo': 'Gráfico 5', 'descripcion': 'Ejemplo: distribución por categoría.',
            'categorias': categorias_producto, 'valores': valores_producto,
        },
        'grafico-6': {
            'titulo': 'Gráfico 6', 'descripcion': 'Ejemplo: relación entre dos métricas.',
            'puntos': [
                {'x': 60000, 'y': 8000}, {'x': 90000, 'y': 15000}, {'x': 110000, 'y': 22000},
                {'x': 135000, 'y': 28000}, {'x': 150000, 'y': 32000}, {'x': 180000, 'y': 45000},
                {'x': 200000, 'y': 52000}, {'x': 220000, 'y': 60000}, {'x': 245000, 'y': 70000},
                {'x': 260000, 'y': 80000},
            ],
        },
        'tabla-1': {
            'titulo': 'Tabla 1', 'descripcion': 'Ejemplo: detalle por producto.',
            'columnas': ['Producto', 'Categoría', 'Ventas (USD)', 'Costo (USD)', 'Ganancia (USD)', 'Margen (%)', 'Unidades', '% del total'],
            'filas': [
                ['Producto A', 'Electrónica', 245000, 150000, 95000, '38.8%', '1,250', 32.9],
                ['Producto B', 'Hogar', 180000, 110000, 70000, '38.9%', '980', 24.2],
                ['Producto C', 'Moda', 135000, 80000, 55000, '40.7%', '760', 18.1],
                ['Producto D', 'Deportes', 98000, 60000, 38000, '38.8%', '540', 13.2],
                ['Producto E', 'Belleza', 87000, 50000, 37000, '42.5%', '430', 11.7],
            ],
            'total': ['Total', '', 745000, 450000, 295000, '39.6%', '3,960', 100.0],
        },
        'tabla-2': {
            'titulo': 'Tabla 2', 'descripcion': 'Ejemplo: detalle por región.',
            'columnas': ['Región', 'Ventas (USD)', '% del total'],
            'filas': [
                ['Norte', 230000, 30.9], ['Centro', 180000, 24.2], ['Sur', 165000, 22.1],
                ['Este', 120000, 16.1], ['Oeste', 50000, 6.7],
            ],
            'total': ['Total', 745000, 100.0],
        },
        'tabla-3': {
            'titulo': 'Tabla 3', 'descripcion': 'Ejemplo: detalle por vendedor.',
            'columnas': ['Vendedor', 'Ventas (USD)', 'Unidades', '% del total'],
            'filas': [
                ['María López', 145000, '780', 25.0],
                ['Juan Pérez', 130000, '650', 22.4],
                ['Ana Torres', 120000, '600', 20.7],
                ['Carlos Ruiz', 100000, '520', 17.2],
                ['Luis García', 85000, '410', 14.7],
            ],
            'total': ['Total', 580000, '2,960', 100.0],
        },
        'tabla-4': {
            'titulo': 'Tabla 4', 'descripcion': 'Ejemplo: detalle por canal de venta.',
            'columnas': ['Canal', 'Ventas (USD)', 'Unidades', '% del total'],
            'filas': [
                ['Tienda física', 320000, '1,540', 43.0],
                ['E-commerce', 250000, '1,180', 33.6],
                ['Marketplace', 175000, '820', 23.5],
            ],
            'total': ['Total', 745000, '3,540', 100.0],
        },
        'tabla-5': {
            'titulo': 'Tabla 5', 'descripcion': 'Ejemplo: detalle por mes.',
            'columnas': ['Mes', 'Ventas (USD)', 'Unidades', '% del total'],
            'filas': [
                ['Enero', 120000, '600', 16.1],
                ['Febrero', 135000, '650', 18.1],
                ['Marzo', 150000, '700', 20.1],
                ['Abril', 170000, '780', 22.8],
                ['Mayo', 170000, '810', 22.8],
            ],
            'total': ['Total', 745000, '3,540', 100.0],
        },
    }


def _rankear_categorias(columnas):
    """Columnas de categoría ordenadas de menor a mayor cardinalidad (las de menor cardinalidad
    agrupan mejor) — mismo criterio que `generic_charts._mejor_columna_serie`."""
    return sorted((c for c in columnas if c['apta_para_categoria']), key=lambda c: c['valores_unicos'])


def _rankear_valores(columnas):
    """Columnas numéricas ordenadas por completitud (menos nulos primero) — mismo criterio que
    `generic_charts._mejor_par_columnas_numericas`."""
    return sorted((c for c in columnas if c['apta_para_valor']), key=lambda c: c['valores_no_nulos'], reverse=True)


def sugerir_mapeo(columnas):
    """Elige, de forma determinista, qué columna(s) usar para cada una de las 15 posiciones —
    reutilizando columnas entre posiciones cuando hay pocas disponibles, evitando repetir la
    misma cuando hay suficientes. Una posición cuyo requisito estructural no se puede cumplir
    (p. ej. Gráfico 3 necesita dos columnas de categoría y el archivo solo trae una) queda con
    `disponible=False`; `calcular_datos_mapeo` conserva el dato ficticio en ese caso."""
    categorias = _rankear_categorias(columnas)
    valores = _rankear_valores(columnas)

    def categoria(i):
        return categorias[i % len(categorias)]['nombre'] if categorias else None

    def valor(i):
        return valores[i % len(valores)]['nombre'] if valores else None

    mapeo = {}

    for i in range(4):
        disponible = bool(valores)
        mapeo[f'kpi-{i + 1}'] = {
            'disponible': disponible, 'columna_valor': valor(i) if disponible else None, 'tipo_agregacion': 'suma',
        }

    disponible_g1 = bool(categorias) and bool(valores)
    mapeo['grafico-1'] = {
        'disponible': disponible_g1,
        'columna_categoria': categoria(0) if disponible_g1 else None,
        'columna_valor': valor(0) if disponible_g1 else None,
        'chart_type': _SLOTS_POR_ID['grafico-1']['chart_type'],
    }

    disponible_g2 = bool(categorias) and len(valores) >= 2
    mapeo['grafico-2'] = {
        'disponible': disponible_g2,
        'columna_categoria': categoria(1) if disponible_g2 else None,
        'columnas_valor': [valor(0), valor(1)] if disponible_g2 else [],
        'chart_type': _SLOTS_POR_ID['grafico-2']['chart_type'],
    }

    disponible_g3 = len(categorias) >= 2 and bool(valores)
    mapeo['grafico-3'] = {
        'disponible': disponible_g3,
        'columna_categoria': categoria(0) if disponible_g3 else None,
        'columna_serie': categoria(1) if disponible_g3 else None,
        'columna_valor': valor(0) if disponible_g3 else None,
        'chart_type': _SLOTS_POR_ID['grafico-3']['chart_type'],
    }

    disponible_g45 = bool(categorias) and bool(valores)
    for slot_id in ('grafico-4', 'grafico-5'):
        mapeo[slot_id] = {
            'disponible': disponible_g45,
            'columna_categoria': categoria(2) if disponible_g45 else None,
            'columna_valor': valor(1) if disponible_g45 else None,
            'chart_type': _SLOTS_POR_ID[slot_id]['chart_type'],
        }

    par_dispersion = generic_charts._mejor_par_columnas_numericas(valores)
    mapeo['grafico-6'] = {
        'disponible': bool(par_dispersion),
        'columna_valor': par_dispersion[0] if par_dispersion else None,
        'columna_valor_y': par_dispersion[1] if par_dispersion else None,
    }

    def columna_valor_tabla(i):
        # Sugerencia automática: siempre arranca en "suma" (mismo criterio que antes de la
        # sección 23) — el usuario puede cambiarlo a "promedio" o "conteo_unicos" por columna.
        return {'columna': valor(i), 'tipo_agregacion': 'suma'}

    disponible_t1 = bool(categorias) and bool(valores)
    mapeo['tabla-1'] = {
        'disponible': disponible_t1,
        'columna_id': categoria(0) if disponible_t1 else None,
        'columnas_valor': [columna_valor_tabla(i) for i in range(min(3, len(valores)))] if disponible_t1 else [],
    }

    disponible_t2 = len(categorias) >= 2 and bool(valores)
    mapeo['tabla-2'] = {
        'disponible': disponible_t2,
        'columna_id': categoria(1) if disponible_t2 else None,
        'columnas_valor': [columna_valor_tabla(0)] if disponible_t2 else [],
    }

    disponible_t3 = len(categorias) >= 3 and len(valores) >= 2
    mapeo['tabla-3'] = {
        'disponible': disponible_t3,
        'columna_id': categoria(2) if disponible_t3 else None,
        'columnas_valor': [columna_valor_tabla(0), columna_valor_tabla(1)] if disponible_t3 else [],
    }

    # Tabla 4 y Tabla 5 son las posiciones históricas (ver módulo): estructuralmente son una tabla
    # más, mismo requisito que Tabla 3, solo rotan a otras columnas de categoría para no repetir
    # siempre la misma combinación.
    disponible_t4 = len(categorias) >= 3 and len(valores) >= 2
    mapeo['tabla-4'] = {
        'disponible': disponible_t4,
        'columna_id': categoria(3) if disponible_t4 else None,
        'columnas_valor': [columna_valor_tabla(0), columna_valor_tabla(1)] if disponible_t4 else [],
    }

    disponible_t5 = len(categorias) >= 3 and len(valores) >= 2
    mapeo['tabla-5'] = {
        'disponible': disponible_t5,
        'columna_id': categoria(4) if disponible_t5 else None,
        'columnas_valor': [columna_valor_tabla(0), columna_valor_tabla(1)] if disponible_t5 else [],
    }

    return mapeo


def _aplicar_filtro_slot(df, propuesta):
    """Filtra el archivo a las filas donde `columna_filtro` == `valor_filtro` (ambos opcionales,
    parte de la propuesta de mapeo de la posición) — aplica igual sin importar el `calculo` de la
    posición, así que sirve tanto para un KPI como para cualquier gráfica o tabla. Sin filtro
    elegido, devuelve el archivo tal cual. Si la columna de filtro ya no existe, `None` (la
    posición cae al dato ficticio, igual que con cualquier otra columna inválida). Un valor que no
    coincide con ninguna fila no es un error: el resultado real es simplemente vacío/cero."""
    columna_filtro = propuesta.get('columna_filtro')
    valor_filtro = propuesta.get('valor_filtro')
    if not columna_filtro or valor_filtro in (None, ''):
        return df
    if columna_filtro not in df.columns:
        return None
    return df[df[columna_filtro].astype(str) == str(valor_filtro)]


def _descripcion_con_filtro(descripcion, propuesta):
    """Agrega "donde <columna_filtro> = <valor_filtro>" al final de una descripción ya armada
    (que siempre termina en '.') cuando la posición tiene un filtro elegido."""
    columna_filtro = propuesta.get('columna_filtro')
    valor_filtro = propuesta.get('valor_filtro')
    if not columna_filtro or valor_filtro in (None, ''):
        return descripcion
    return f'{descripcion[:-1]} donde "{columna_filtro}" = "{valor_filtro}".'


def _calcular_contenido_slot(df, slot, propuesta):
    """Calcula el contenido real de una posición a partir de la propuesta de mapeo (ya
    confirmada/ajustada por el usuario). `None` si falta alguna columna requerida o si la
    columna elegida (de cálculo o de filtro) ya no existe en el archivo — en ese caso el llamador
    cae al dato ficticio."""
    calculo = slot['calculo']
    titulo = slot['titulo']

    df = _aplicar_filtro_slot(df, propuesta)
    if df is None:
        return None

    if calculo == 'kpi':
        columna_valor = propuesta.get('columna_valor')
        if not columna_valor:
            return None
        if propuesta.get('tipo_agregacion') == 'conteo_unicos':
            datos = generic_charts.generar_conteo_valores_unicos(df, columna_valor)
            if not datos:
                return None
            return {
                'titulo': titulo,
                'descripcion': _descripcion_con_filtro(f'Cantidad de valores únicos de "{columna_valor}".', propuesta),
                'valor': datos['valor'], 'formato': 'numero',
            }
        if propuesta.get('tipo_agregacion') == 'promedio':
            datos = generic_charts.generar_promedio_columna(df, columna_valor)
            if not datos:
                return None
            return {
                'titulo': titulo,
                'descripcion': _descripcion_con_filtro(f'Promedio de "{columna_valor}".', propuesta),
                'valor': datos['valor'], 'formato': 'numero',
            }
        datos = generic_charts.generar_datos_grafica(df, columna_valor, None)
        if not datos:
            return None
        return {
            'titulo': titulo, 'descripcion': _descripcion_con_filtro(f'Suma de "{columna_valor}".', propuesta),
            'valor': datos['valor'], 'formato': 'numero',
        }

    if calculo == 'chart':
        columna_categoria = propuesta.get('columna_categoria')
        columna_valor = propuesta.get('columna_valor')
        if not columna_categoria or not columna_valor:
            return None
        datos = generic_charts.generar_datos_grafica(df, columna_valor, columna_categoria)
        if not datos:
            return None
        return {
            'titulo': titulo,
            'descripcion': _descripcion_con_filtro(f'Suma de "{columna_valor}" agrupada por "{columna_categoria}".', propuesta),
            'categorias': datos['categorias'], 'valores': datos['valores'],
        }

    if calculo == 'multivalor':
        columna_categoria = propuesta.get('columna_categoria')
        columnas_valor = propuesta.get('columnas_valor') or []
        if not columna_categoria or not columnas_valor:
            return None
        datos = generic_charts.generar_datos_multivalor(df, columna_categoria, columnas_valor)
        if not datos:
            return None
        return {
            'titulo': titulo,
            'descripcion': _descripcion_con_filtro(f'Comparación de {" y ".join(columnas_valor)} por "{columna_categoria}".', propuesta),
            'categorias': datos['categorias'], 'series': datos['series'],
        }

    if calculo == 'multiserie':
        columna_categoria = propuesta.get('columna_categoria')
        columna_serie = propuesta.get('columna_serie')
        columna_valor = propuesta.get('columna_valor')
        if not columna_categoria or not columna_serie or not columna_valor:
            return None
        datos = generic_charts.generar_datos_multiserie(df, columna_valor, columna_categoria, columna_serie)
        if not datos:
            return None
        return {
            'titulo': titulo,
            'descripcion': _descripcion_con_filtro(
                f'Suma de "{columna_valor}" agrupada por "{columna_categoria}" y "{columna_serie}".', propuesta,
            ),
            'categorias': datos['categorias'], 'series': datos['series'],
        }

    if calculo == 'dispersion':
        columna_valor = propuesta.get('columna_valor')
        columna_valor_y = propuesta.get('columna_valor_y')
        if not columna_valor or not columna_valor_y:
            return None
        datos = generic_charts.generar_datos_dispersion(df, columna_valor, columna_valor_y)
        if not datos:
            return None
        return {
            'titulo': titulo,
            'descripcion': _descripcion_con_filtro(f'Relación entre "{columna_valor}" y "{columna_valor_y}".', propuesta),
            'puntos': datos['puntos'],
        }

    if calculo == 'tabla':
        columna_id = propuesta.get('columna_id')
        columnas_valor = propuesta.get('columnas_valor') or []
        if not columna_id or not columnas_valor:
            return None
        datos = generic_charts.generar_datos_tabla(df, columna_id, columnas_valor)
        if not datos:
            return None
        # Los nombres de columna de valor ya resueltos (cada entrada de `columnas_valor` puede ser
        # un dict `{columna, tipo_agregacion}` o, por compatibilidad, un string plano) — se leen de
        # `datos['columnas']` en vez de volver a normalizar acá para no duplicar ese criterio.
        nombres_valor = datos['columnas'][1:-1]
        return {
            'titulo': titulo,
            'descripcion': _descripcion_con_filtro(f'Detalle de {" y ".join(nombres_valor)} por "{columna_id}".', propuesta),
            'columnas': datos['columnas'], 'filas': datos['filas'], 'total': datos['total'],
        }

    return None


def calcular_datos_mapeo(df, mapeo):
    """Contenido final de las 15 posiciones: el calculado a partir del mapeo cuando la posición
    está `disponible` y sus columnas siguen existiendo, o el dato ficticio en cualquier otro
    caso — nunca deja una posición sin contenido."""
    fijos = datos_ficticios()
    resultado = {}
    for slot in PLANTILLA_SLOTS:
        slot_id = slot['id']
        propuesta = mapeo.get(slot_id) or {}
        contenido = _calcular_contenido_slot(df, slot, propuesta) if propuesta.get('disponible') else None
        resultado[slot_id] = contenido or fijos[slot_id]
    return resultado


def slots_efectivos():
    """Los 13 slots a usar para sembrar un dashboard NUEVO real: la disposición (orden, ancho,
    alto, visibilidad), tipo de gráfico, color y título/descripción que un administrador haya
    personalizado en "Configuración → Plantilla base" (los `DashboardComponent` de
    `DASHBOARD_ID_PLANTILLA_BASE`), si existen — o si no, `PLANTILLA_SLOTS` tal cual (todavía sin
    personalizar, o primer arranque antes de que la plantilla base se haya sembrado siquiera).
    `id`/`tipo`/`calculo` nunca se personalizan: son estructurales, deciden qué función de
    `generic_charts` calcula esa posición y no tiene sentido exponerlos como editables."""
    personalizados = {
        c.component_id: c
        for c in DashboardComponent.objects.filter(layout__dashboard_id=DASHBOARD_ID_PLANTILLA_BASE)
    }
    if not personalizados:
        return PLANTILLA_SLOTS

    resultado = []
    for indice, slot in enumerate(PLANTILLA_SLOTS):
        componente = personalizados.get(slot['id'])
        if not componente:
            resultado.append({**slot, '_orden': indice + 1})
            continue

        nuevo = {
            **slot,
            'ancho': componente.width, 'alto': componente.height,
            'chart_type': componente.chart_type or slot['chart_type'],
            'config_fijo': componente.config,
            'is_visible': componente.is_visible,
            '_orden': componente.order,
        }
        color_personalizado = (componente.styles or {}).get('colorPrincipal')
        if color_personalizado:
            nuevo['color_defecto'] = color_personalizado
        contenido = componente.content or {}
        if contenido.get('titulo'):
            nuevo['titulo_personalizado'] = contenido['titulo']
        if contenido.get('descripcion'):
            nuevo['descripcion_personalizada'] = contenido['descripcion']
        resultado.append(nuevo)

    resultado.sort(key=lambda s: s['_orden'])
    return resultado


def _construir_componente(slot, orden, contenido, propuesta=None):
    chart_type = _chart_type_elegido(slot, propuesta)
    config = dict(slot.get('config_fijo') or {})
    if chart_type in dashboard_layout.TIPOS_CON_LEYENDA:
        config['leyenda_posicion'] = dashboard_layout.LEYENDA_POSICION_POR_DEFECTO
    styles = {'colorPrincipal': slot['color_defecto']} if slot.get('color_defecto') else {}
    contenido = dict(contenido)
    if slot.get('titulo_personalizado'):
        contenido['titulo'] = slot['titulo_personalizado']
    if slot.get('descripcion_personalizada'):
        contenido['descripcion'] = slot['descripcion_personalizada']
    return {
        'component_id': slot['id'], 'type': slot['tipo'], 'chart_type': chart_type,
        'row': 1, 'order': orden, 'width': slot['ancho'], 'height': slot['alto'],
        'is_visible': slot.get('is_visible', True),
        'content': contenido, 'styles': styles, 'config': config, 'mapeo': propuesta or {},
    }


def _componentes_zona_personal(layout):
    """Los componentes que el usuario agregó a mano a la "Zona Personal" (`config.zona ==
    'personal'`, ver `dashboard_layout.agregar_componente_generado`) — se preservan tal cual (sin
    recalcular contra el archivo nuevo) cada vez que se vuelve a sembrar/aplicar la plantilla de
    15 posiciones: recalcular abriría una superficie nueva de "la columna ya no existe" que la
    plantilla fija ya resuelve cayendo a datos ficticios, pero un componente de Zona Personal no
    tiene ese resguardo. Se lee directo de `DashboardComponent` (no de `componentes_validos`, que
    no expone `is_visible`) para no perder el estado oculto de cada uno."""
    return [
        {
            'component_id': c.component_id, 'type': c.type, 'chart_type': c.chart_type,
            'row': c.row, 'order': c.order, 'width': c.width, 'height': c.height,
            'is_visible': c.is_visible, 'content': c.content, 'styles': c.styles,
            'config': c.config, 'mapeo': c.mapeo,
        }
        for c in DashboardComponent.objects.filter(layout=layout)
        if (c.config or {}).get('zona') == 'personal'
    ]


def _escribir_plantilla(dashboard_id, contenidos_por_slot, mapeo=None, slots=None):
    slots = slots if slots is not None else PLANTILLA_SLOTS
    mapeo = mapeo or {}
    layout = dashboard_layout.obtener_o_crear_layout(dashboard_id)
    personales = _componentes_zona_personal(layout)
    componentes = [
        _construir_componente(slot, i + 1, contenidos_por_slot[slot['id']], mapeo.get(slot['id']))
        for i, slot in enumerate(slots)
    ] + [{**c, 'order': len(slots) + i + 1} for i, c in enumerate(personales)]
    dashboard_layout._escribir_componentes(layout, componentes)
    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])
    return layout


def sembrar_plantilla(dashboard_id):
    """Crea los 15 componentes de la plantilla con datos ficticios, siempre a partir de los
    valores de fábrica (`PLANTILLA_SLOTS`, patrón Z) — nunca de la personalización. Reservada para
    dos casos: el primer arranque de la propia plantilla base (`DASHBOARD_ID_PLANTILLA_BASE`) y el
    botón "Restablecer al patrón Z" (volver a sembrarla). Un dashboard real nuevo se siembra con
    `sembrar_plantilla_desde_base`, que sí respeta la personalización vigente."""
    return _escribir_plantilla(dashboard_id, datos_ficticios())


def sembrar_plantilla_desde_base(dashboard_id):
    """Como `sembrar_plantilla`, pero usa `slots_efectivos()` — la disposición/tipo de gráfico/
    color/título personalizados en "Configuración → Plantilla base", si los hay. Es la que siembra
    todo dashboard real nuevo (`services.dashboards.crear_dashboard`, incluidas sus pestañas)."""
    return _escribir_plantilla(dashboard_id, datos_ficticios(), slots=slots_efectivos())


def aplicar_mapeo(dashboard_id, df, mapeo, actor=None, request=None):
    """Recalcula las 15 posiciones a partir de un mapeo ya confirmado por el usuario y
    sobreescribe los mismos 15 componentes (nunca agrega otros) — se puede llamar varias veces
    (p. ej. tras cargar un archivo distinto) sin duplicar nada. El `chart_type` de cada posición
    (`_chart_type_elegido`) también sale del mapeo, así que cambiar cómo se dibuja una gráfica (p.
    ej. de barras a líneas) se aplica junto con el resto de ajustes."""
    contenidos = calcular_datos_mapeo(df, mapeo)
    layout = _escribir_plantilla(dashboard_id, contenidos, mapeo)

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_TEMPLATE_APPLIED', actor=actor,
        dashboard_id=dashboard_id, metadata={'version': layout.version}, request=request,
    )
    return layout
