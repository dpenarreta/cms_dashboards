"""Estructura fija del "Dashboard Directorio" (réplica de la pestaña "6. Cartera" de un informe).

Este dashboard es la excepción declarada del proyecto: no usa las 13 posiciones de la plantilla
genérica sino 7 componentes propios, con sus propios cálculos (`tramos_antiguedad`,
`cumplimiento_metas`, `concentracion`), anchos, altos y colores. Las 13 posiciones de fábrica se
ocultan y se bloquean para que no convivan KPIs ficticios genéricos junto a la estructura real.

La especificación de abajo es la MISMA que sembró la migración `0021_sembrar_cartera_dashboard_
directorio` (ids, títulos, filtros, colores, metas, `top_n`). La diferencia es de dónde sale el
contenido: la migración sembró valores ficticios coherentes —no podía importar `services/`—,
mientras que acá se calcula de verdad, contra un archivo real, con los mismos servicios que usa
cualquier otro dashboard. El mapeo se guarda en cada componente, así que "Configurar componente →
Datos" sigue funcionando encima de esto.

Lo único que NO hereda de la plantilla genérica es la disposición. Todo lo demás —el contrato de
error, los permisos, la auditoría, los servicios de cálculo— es el mismo de siempre.
"""

from ..models import DashboardComponent, DashboardLayout
from . import dashboard_layout, plantilla

IDS_FABRICA = [
    'kpi-1', 'kpi-2', 'kpi-3', 'kpi-4',
    'grafico-1', 'grafico-2', 'grafico-3', 'grafico-4', 'grafico-5', 'grafico-6',
    'tabla-1', 'tabla-2', 'tabla-3',
]

COLUMNA_VALOR = 'Saldo'
COLUMNA_FECHA = 'Fecha de Vencimiento'
COLUMNA_CLIENTE = 'Cliente'

_DORADO, _VERDE, _AZUL = '#D4AF37', '#2E7D32', '#1E88E5'
_ROJO, _GRANATE, _CORAL, _ROSA = '#C62828', '#8B1E1E', '#EF9A9A', '#F48FB1'

TRAMOS = ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días']
# De "sano" a "preocupante", alineado posicionalmente con `TRAMOS`.
COLORES_TRAMOS = [_VERDE, _AZUL, _DORADO, _CORAL, _ROSA, _GRANATE]

# Metas por tramo, alineadas con `ETIQUETAS_TRAMOS_ACUMULADOS`: las cinco primeras filas son
# acumuladas y se exigen crecientes; la última es la cola >120 días, que se acota por arriba.
METAS_CUMPLIMIENTO = [
    {'meta_min': 50}, {'meta_min': 70}, {'meta_min': 80},
    {'meta_min': 90}, {'meta_min': 95}, {'meta_max': 5},
]

TOP_N_CONCENTRACION = 16

KPI_ANCHO, KPI_ALTO = 3, 180
PANEL_ANCHO, GRAFICO_ALTO, TABLA_ALTO = 6, 420, 380

# `dias_filtro` se compara contra los días transcurridos desde la fecha de vencimiento hasta la
# fecha de corte: `menor_igual 0` son las facturas que todavía no vencieron, `mayor 0` las vencidas.
_KPIS = [
    {'id': 'cartera-total', 'titulo': 'Cartera total', 'color': _DORADO, 'filtro': None},
    {'id': 'al-corriente', 'titulo': 'Al corriente', 'color': _VERDE,
     'filtro': {'operador_filtro': 'menor_igual', 'dias_filtro': 0}},
    {'id': 'vencida-total', 'titulo': 'Vencida total', 'color': _ROJO,
     'filtro': {'operador_filtro': 'mayor', 'dias_filtro': 0}},
    {'id': 'vencida-mas-120-dias', 'titulo': 'Vencida +120 días', 'color': _GRANATE,
     'filtro': {'operador_filtro': 'mayor', 'dias_filtro': 120}},
]


def _mapeo_kpi(filtro):
    mapeo = {'disponible': True, 'calculo': 'kpi', 'columna_valor': COLUMNA_VALOR, 'formato': 'moneda'}
    if filtro:
        mapeo.update({
            'columna_filtro': COLUMNA_FECHA, 'tipo_filtro': 'dias_vencidos',
            'operador_filtro': filtro['operador_filtro'], 'dias_filtro': filtro['dias_filtro'],
        })
    return mapeo


def especificacion():
    """Los 7 componentes, sin contenido todavía: `(component_id, titulo, tipo, chart_type, ancho,
    alto, styles, mapeo)`. Separado del cálculo para poder inspeccionar la estructura sin un
    archivo."""
    componentes = [
        {
            'component_id': kpi['id'], 'titulo': kpi['titulo'], 'type': 'kpi', 'chart_type': '',
            'width': KPI_ANCHO, 'height': KPI_ALTO,
            'styles': {'colorPrincipal': kpi['color']}, 'mapeo': _mapeo_kpi(kpi['filtro']),
        }
        for kpi in _KPIS
    ]
    componentes.append({
        'component_id': 'antiguedad-de-cartera', 'titulo': 'Antigüedad de cartera',
        'type': 'chart', 'chart_type': 'barras_verticales',
        'width': PANEL_ANCHO, 'height': GRAFICO_ALTO,
        'styles': {'coloresPorCategoria': dict(zip(TRAMOS, COLORES_TRAMOS))},
        'mapeo': {
            'disponible': True, 'calculo': 'tramos_antiguedad',
            'columna_fecha': COLUMNA_FECHA, 'columna_valor': COLUMNA_VALOR,
        },
    })
    componentes.append({
        'component_id': 'cumplimiento-metas-antiguedad', 'titulo': 'Cumplimiento de metas de antigüedad',
        'type': 'chart', 'chart_type': 'tabla',
        'width': PANEL_ANCHO, 'height': TABLA_ALTO, 'styles': {},
        'mapeo': {
            'disponible': True, 'calculo': 'cumplimiento_metas',
            'columna_fecha': COLUMNA_FECHA, 'columna_valor': COLUMNA_VALOR,
            'metas': [dict(meta) for meta in METAS_CUMPLIMIENTO],
        },
    })
    componentes.append({
        'component_id': 'concentracion-de-cartera', 'titulo': 'Concentración de cartera',
        'type': 'chart', 'chart_type': 'tabla',
        'width': 12, 'height': TABLA_ALTO, 'styles': {},
        'mapeo': {
            'disponible': True, 'calculo': 'concentracion',
            'columna_id': COLUMNA_CLIENTE, 'columna_valor': COLUMNA_VALOR,
            'top_n': TOP_N_CONCENTRACION,
        },
    })
    return componentes


def columnas_requeridas():
    return [COLUMNA_VALOR, COLUMNA_FECHA, COLUMNA_CLIENTE]


def columnas_faltantes(df):
    return [columna for columna in columnas_requeridas() if columna not in df.columns]


def _componentes_de_fabrica_ocultos(layout, orden_desde):
    """Las 13 posiciones de la plantilla, ocultas y bloqueadas, conservando lo demás tal cual.

    Se conservan en vez de borrarse para no perder su mapeo: si alguna vez se quiere volver al
    dashboard genérico, alcanza con volver a mostrarlas.
    """
    componentes = []
    for i, componente in enumerate(layout.components.filter(component_id__in=IDS_FABRICA).order_by('order')):
        componentes.append({
            'component_id': componente.component_id, 'type': componente.type,
            'chart_type': componente.chart_type, 'row': 1, 'order': orden_desde + i,
            'width': componente.width, 'height': componente.height, 'is_visible': False,
            'content': componente.content or {}, 'styles': componente.styles or {},
            'config': {**(componente.config or {}), 'bloqueado': True},
            'mapeo': componente.mapeo or {},
        })
    return componentes


def construir(dashboard_id, df, fecha_referencia=None):
    """Recalcula los 7 componentes contra `df` y reescribe el layout completo.

    Devuelve la lista de `(component_id, hubo_contenido)` para que el llamador informe qué se pudo
    calcular. Un componente sin contenido (columna ausente, archivo vacío) conserva la estructura
    pero queda sin datos, en vez de romper la carga entera.
    """
    layout = dashboard_layout.obtener_o_crear_layout(dashboard_id)

    componentes = []
    resultados = []
    for orden, spec in enumerate(especificacion(), start=1):
        contenido = plantilla.calcular_contenido_por_calculo(
            df, spec['mapeo']['calculo'], spec['titulo'], spec['mapeo'],
            dashboard_id=dashboard_id, fecha_referencia=fecha_referencia,
        )
        resultados.append((spec['component_id'], contenido is not None))
        componentes.append({
            'component_id': spec['component_id'], 'type': spec['type'],
            'chart_type': spec['chart_type'], 'row': 1, 'order': orden,
            'width': spec['width'], 'height': spec['height'], 'is_visible': True,
            'content': contenido or {'titulo': spec['titulo']},
            'styles': spec['styles'],
            # `zona: personal` es lo que hace que el frontend los trate como componentes propios y
            # no como posiciones de la plantilla; `bloqueado` impide que un usuario no superusuario
            # los mueva, redimensione, oculte o borre.
            'config': {'zona': 'personal', 'bloqueado': True},
            'mapeo': spec['mapeo'],
        })

    componentes.extend(_componentes_de_fabrica_ocultos(layout, len(componentes) + 1))

    dashboard_layout._escribir_componentes(layout, componentes)
    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])
    return resultados


def esta_sembrado(dashboard_id):
    layout = DashboardLayout.objects.filter(dashboard_id=dashboard_id).first()
    if layout is None:
        return False
    return DashboardComponent.objects.filter(layout=layout, component_id='cartera-total').exists()
