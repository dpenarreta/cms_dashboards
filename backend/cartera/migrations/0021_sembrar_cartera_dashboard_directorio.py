"""Siembra la réplica de la pestaña "6. Cartera" de un mockup de informe financiero
(`Mockup_Directorio_Cartera_Junio2026.pdf`) en el dashboard `dashboard-directorio` ("Dashboard
Directorio", ya existente): 4 KPI (con filtro "Días desde una fecha" para 3 de ellos), un gráfico
de antigüedad por tramos, una tabla de cumplimiento de metas por tramo y una tabla de
concentración top-N — todos con `config.bloqueado=True` (ver `services/dashboard_layout.py::
validar_componentes`: un usuario normal no puede moverlos/redimensionarlos/ocultarlos/eliminarlos,
un superusuario sí). Las 13 posiciones de fábrica de la plantilla (`kpi-1..4`, `grafico-1..6`,
`tabla-1..3`) se ocultan (`is_visible=False`) y también quedan bloqueadas, para que un usuario
normal no pueda "Mostrar" un KPI ficticio genérico junto a la estructura real de Cartera.

No es destructiva de datos reales: si el dashboard no existe en este entorno (no todos lo tienen),
no hace nada. Los 7 componentes nuevos nacen con contenido y mapeo ficticios (mismo criterio que
`plantilla.py::datos_ficticios()` para las 13 posiciones de fábrica) — el mapeo de columnas
(`Saldo`, `Fecha de Vencimiento`, `Cliente`) es real, así que en cuanto se conecte un archivo/BD
con esas columnas y se reabra "Configurar componente → Datos" en cada uno (el mapeo bloqueado
sigue siendo editable — el bloqueo es solo estructural), el contenido pasa a ser real.

Como el resto de migraciones de datos de esta app (ver `0012_backfill_tablas_historicas.py`), NO
importa código de `cartera/services/` — usa modelos históricos (`apps.get_model`) y valores ya
calculados a mano, para que esta migración siga produciendo el mismo resultado aunque el código
vivo cambie después."""

from django.db import migrations

DASHBOARD_ID = 'dashboard-directorio'

IDS_FABRICA = [
    'kpi-1', 'kpi-2', 'kpi-3', 'kpi-4',
    'grafico-1', 'grafico-2', 'grafico-3', 'grafico-4', 'grafico-5', 'grafico-6',
    'tabla-1', 'tabla-2', 'tabla-3',
]

# Copia congelada de `generic_charts.py::ETIQUETAS_TRAMOS_ANTIGUEDAD`/`ETIQUETAS_TRAMOS_ACUMULADOS`
# al momento de esta migración — a propósito no se importa el módulo real (mismo criterio que el
# resto de migraciones de datos de esta app).
_TRAMOS_ANTIGUEDAD = ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días']

_DESCRIPCION_FICTICIA = 'Dato de ejemplo — se reemplaza al cargar un archivo.'

# Acentos de color calcados del mockup (borde izquierdo de cada KPI — dorado/verde/rojo/granate —
# y una barra por tramo en el gráfico de antigüedad, de "sano" a "preocupante"). Aproximación
# visual del PDF, no un muestreo exacto de píxel — alcance acordado con el usuario: solo colores/
# acentos por componente, usando `styles.colorPrincipal`/`styles.coloresPorCategoria`, el mismo
# mecanismo que ya existe para cualquier KPI/gráfico (`GenericKpiCard.jsx`/`GenericBarChart.jsx`).
_COLOR_DORADO = '#D4AF37'
_COLOR_VERDE = '#2E7D32'
_COLOR_AZUL = '#1E88E5'
_COLOR_ROJO = '#C62828'
_COLOR_GRANATE = '#8B1E1E'
_COLOR_CORAL = '#EF9A9A'
_COLOR_ROSA = '#F48FB1'

# Componentes nuevos, en el orden en que aparecen en el mockup. `valor`/`filas` son ficticios pero
# internamente consistentes entre sí (la suma de los tramos de antigüedad da el total del primer
# KPI, el acumulado de la tabla de cumplimiento coincide con esos mismos tramos, etc.) — no son
# los datos reales del mockup (una empresa real, confidencial), solo un ejemplo coherente hasta
# que se cargue un archivo real.
_KPIS = [
    {
        'component_id': 'cartera-total', 'titulo': 'Cartera total', 'valor': 500000,
        'filtro': None, 'color': _COLOR_DORADO,
    },
    {
        'component_id': 'al-corriente', 'titulo': 'Al corriente', 'valor': 310000,
        'filtro': {'operador_filtro': 'menor_igual', 'dias_filtro': 0}, 'color': _COLOR_VERDE,
    },
    {
        'component_id': 'vencida-total', 'titulo': 'Vencida total', 'valor': 190000,
        'filtro': {'operador_filtro': 'mayor', 'dias_filtro': 0}, 'color': _COLOR_ROJO,
    },
    {
        'component_id': 'vencida-mas-120-dias', 'titulo': 'Vencida +120 días', 'valor': 25000,
        'filtro': {'operador_filtro': 'mayor', 'dias_filtro': 120}, 'color': _COLOR_GRANATE,
    },
]

# Alineado posicionalmente con `_TRAMOS_ANTIGUEDAD` — mismo criterio "de sano a preocupante" que
# ya usan las 4 tarjetas KPI de arriba (verde→azul→dorado→coral→rosa→granate).
_COLORES_TRAMOS_ANTIGUEDAD = [_COLOR_VERDE, _COLOR_AZUL, _COLOR_DORADO, _COLOR_CORAL, _COLOR_ROSA, _COLOR_GRANATE]

_TRAMOS_VALORES = [300000.0, 90000.0, 40000.0, 20000.0, 15000.0, 35000.0]  # suma = 500000, alineado con _TRAMOS_ANTIGUEDAD

_CUMPLIMIENTO_FILAS = [
    ['Corriente', 300000.0, 60.0, 'Cumple'],
    ['Vencido ≤ 30 días (acum.)', 390000.0, 78.0, 'Cumple'],
    ['Vencido ≤ 60 días (acum.)', 430000.0, 86.0, 'Cumple'],
    ['Vencido ≤ 90 días (acum.)', 450000.0, 90.0, 'Cumple'],
    ['Vencido ≤ 120 días (acum.)', 465000.0, 93.0, 'No cumple (menor al mínimo (95.0))'],
    ['Más de 120 días', 35000.0, 7.0, 'No cumple (mayor al máximo (5.0))'],
]
_CUMPLIMIENTO_METAS = [
    {'meta_min': 50}, {'meta_min': 70}, {'meta_min': 80}, {'meta_min': 90}, {'meta_min': 95}, {'meta_max': 5},
]

_CONCENTRACION_FILAS = [
    ['Cliente A', 120000.0, 24.0, 24.0],
    ['Cliente B', 90000.0, 18.0, 42.0],
    ['Cliente C', 60000.0, 12.0, 54.0],
    ['Resto (12)', 230000.0, 46.0, 100.0],
]
_CONCENTRACION_TOTAL = ['Total', 500000.0, 100.0, 100.0]

KPI_ANCHO, KPI_ALTO = 3, 180
CHART_ANCHO, CHART_ALTO = 6, 420
TABLA_ALTO = 380


def _componentes_nuevos(orden_inicial):
    config_base = {'zona': 'personal', 'bloqueado': True}
    componentes = []
    orden = orden_inicial

    for kpi in _KPIS:
        mapeo = {
            'disponible': True, 'calculo': 'kpi', 'columna_valor': 'Saldo', 'formato': 'moneda',
        }
        if kpi['filtro']:
            mapeo.update({
                'columna_filtro': 'Fecha de Vencimiento', 'tipo_filtro': 'dias_vencidos',
                'operador_filtro': kpi['filtro']['operador_filtro'], 'dias_filtro': kpi['filtro']['dias_filtro'],
            })
        componentes.append({
            'component_id': kpi['component_id'], 'type': 'kpi', 'chart_type': '',
            'row': 1, 'order': orden, 'width': KPI_ANCHO, 'height': KPI_ALTO, 'is_visible': True,
            'content': {
                'titulo': kpi['titulo'], 'descripcion': _DESCRIPCION_FICTICIA,
                'valor': kpi['valor'], 'formato': 'moneda',
            },
            'styles': {'colorPrincipal': kpi['color']}, 'config': dict(config_base), 'mapeo': mapeo,
        })
        orden += 1

    componentes.append({
        'component_id': 'antiguedad-de-cartera', 'type': 'chart', 'chart_type': 'barras_verticales',
        'row': 1, 'order': orden, 'width': CHART_ANCHO, 'height': CHART_ALTO, 'is_visible': True,
        'content': {
            'titulo': 'Antigüedad de cartera', 'descripcion': _DESCRIPCION_FICTICIA,
            'categorias': list(_TRAMOS_ANTIGUEDAD), 'valores': list(_TRAMOS_VALORES),
        },
        'styles': {'coloresPorCategoria': dict(zip(_TRAMOS_ANTIGUEDAD, _COLORES_TRAMOS_ANTIGUEDAD))},
        'config': dict(config_base), 'mapeo': {
            'disponible': True, 'calculo': 'tramos_antiguedad',
            'columna_fecha': 'Fecha de Vencimiento', 'columna_valor': 'Saldo',
        },
    })
    orden += 1

    componentes.append({
        'component_id': 'cumplimiento-metas-antiguedad', 'type': 'chart', 'chart_type': 'tabla',
        'row': 1, 'order': orden, 'width': CHART_ANCHO, 'height': TABLA_ALTO, 'is_visible': True,
        'content': {
            'titulo': 'Cumplimiento de metas de antigüedad', 'descripcion': _DESCRIPCION_FICTICIA,
            'columnas': ['Tramo', 'Saldo', '% acumulado', 'Resultado'],
            'filas': [list(fila) for fila in _CUMPLIMIENTO_FILAS], 'total': None,
        },
        'styles': {}, 'config': dict(config_base), 'mapeo': {
            'disponible': True, 'calculo': 'cumplimiento_metas',
            'columna_fecha': 'Fecha de Vencimiento', 'columna_valor': 'Saldo',
            'metas': [dict(meta) for meta in _CUMPLIMIENTO_METAS],
        },
    })
    orden += 1

    componentes.append({
        'component_id': 'concentracion-de-cartera', 'type': 'chart', 'chart_type': 'tabla',
        'row': 1, 'order': orden, 'width': 12, 'height': TABLA_ALTO, 'is_visible': True,
        'content': {
            'titulo': 'Concentración de cartera', 'descripcion': _DESCRIPCION_FICTICIA,
            'columnas': ['Cliente', 'Saldo', '% del total', '% acumulado'],
            'filas': [list(fila) for fila in _CONCENTRACION_FILAS], 'total': list(_CONCENTRACION_TOTAL),
        },
        'styles': {}, 'config': dict(config_base), 'mapeo': {
            'disponible': True, 'calculo': 'concentracion',
            'columna_id': 'Cliente', 'columna_valor': 'Saldo', 'top_n': 16,
        },
    })

    return componentes


def sembrar_cartera_dashboard_directorio(apps, schema_editor):
    Dashboard = apps.get_model('cartera', 'Dashboard')
    DashboardLayout = apps.get_model('cartera', 'DashboardLayout')
    DashboardComponent = apps.get_model('cartera', 'DashboardComponent')

    if not Dashboard.objects.filter(dashboard_id=DASHBOARD_ID).exists():
        return  # No todos los entornos tienen este dashboard — no es un error, simplemente no aplica.

    layout, _creado = DashboardLayout.objects.get_or_create(dashboard_id=DASHBOARD_ID)

    if DashboardComponent.objects.filter(layout=layout, component_id='cartera-total').exists():
        return  # Ya sembrado (ej. re-ejecución del comando de migraciones) — no duplicar.

    fabrica = list(DashboardComponent.objects.filter(layout=layout, component_id__in=IDS_FABRICA))
    for componente in fabrica:
        componente.is_visible = False
        componente.config = {**(componente.config or {}), 'bloqueado': True}
    DashboardComponent.objects.bulk_update(fabrica, ['is_visible', 'config'])

    orden_maximo = layout.components.order_by('-order').values_list('order', flat=True).first() or 0
    nuevos = [
        DashboardComponent(layout=layout, **datos)
        for datos in _componentes_nuevos(orden_maximo + 1)
    ]
    DashboardComponent.objects.bulk_create(nuevos)

    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])


def revertir(apps, schema_editor):
    Dashboard = apps.get_model('cartera', 'Dashboard')
    DashboardLayout = apps.get_model('cartera', 'DashboardLayout')
    DashboardComponent = apps.get_model('cartera', 'DashboardComponent')

    if not Dashboard.objects.filter(dashboard_id=DASHBOARD_ID).exists():
        return

    try:
        layout = DashboardLayout.objects.get(dashboard_id=DASHBOARD_ID)
    except DashboardLayout.DoesNotExist:
        return

    ids_nuevos = [datos['component_id'] for datos in _componentes_nuevos(0)]
    DashboardComponent.objects.filter(layout=layout, component_id__in=ids_nuevos).delete()

    fabrica = list(DashboardComponent.objects.filter(layout=layout, component_id__in=IDS_FABRICA))
    for componente in fabrica:
        componente.is_visible = True
        config = dict(componente.config or {})
        config.pop('bloqueado', None)
        componente.config = config
    DashboardComponent.objects.bulk_update(fabrica, ['is_visible', 'config'])

    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])


class Migration(migrations.Migration):

    dependencies = [
        ('cartera', '0020_dashboard_fuente_bd_fecha_formato'),
    ]

    operations = [
        migrations.RunPython(sembrar_cartera_dashboard_directorio, revertir),
    ]
