"""Layout configurable del dashboard (secciones 8, 17, 19, 23 del prompt de personalización).

Define el layout por defecto como código (no como datos precargados), valida cualquier layout
entrante contra una lista blanca de componentes conocidos, y clasifica los cambios para la
auditoría. Los componentes del grid (KPIs, gráficos, mensajes, alertas, tablas, título, panel de
filtros) viven en `DashboardComponent`; los 16 campos de filtro individuales se reordenan
*dentro* del componente `panel-filtros` (su propio `config['filtros']`), no como componentes de
grid independientes — mezclarlos con gráficos/KPIs en el mismo grid 2D no aporta valor de UX y
complica el modelo sin necesidad.
"""

import re

from ..exceptions import CarteraError
from ..models import DashboardAuditLog, DashboardComponent, DashboardLayout

ANCHO_MIN, ANCHO_MAX = 1, 12
ALTO_MIN, ALTO_MAX = 60, 1200
LONGITUD_MAXIMA_TITULO = 200
LONGITUD_MAXIMA_DESCRIPCION = 500

_HEX_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
_RGBA_RE = re.compile(
    r'^rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(,\s*(0|1|0?\.\d+)\s*)?\)$'
)

DEFAULT_FILTROS = [
    {'id': 'cliente', 'label': 'Cliente / RUC', 'order': 1, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'ciudad', 'label': 'Ciudad', 'order': 2, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'zona', 'label': 'Zona', 'order': 3, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'sucursal', 'label': 'Sucursal', 'order': 4, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'recuperador', 'label': 'Recuperador', 'order': 5, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'causal', 'label': 'Causal', 'order': 6, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'estado_cartera', 'label': 'Estado de cartera', 'order': 7, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'rango_mora', 'label': 'Rango de mora', 'order': 8, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'producto', 'label': 'Producto', 'order': 9, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'articulo', 'label': 'Artículo', 'order': 10, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'tipo_venta', 'label': 'Tipo de venta', 'order': 11, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'estado_cliente', 'label': 'Estado del cliente', 'order': 12, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'fecha_vencimiento_desde', 'label': 'Vencimiento desde', 'order': 13, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'fecha_vencimiento_hasta', 'label': 'Vencimiento hasta', 'order': 14, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'fecha_emision_desde', 'label': 'Emisión desde', 'order': 15, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
    {'id': 'fecha_emision_hasta', 'label': 'Emisión hasta', 'order': 16, 'width': 2, 'is_visible': True, 'is_required': False, 'scope': 'global'},
]


def _comp(component_id, type_, row, order, width, height, titulo=None, descripcion=None, extra_config=None):
    return {
        'component_id': component_id,
        'type': type_,
        'chart_type': '',
        'row': row,
        'order': order,
        'width': width,
        'height': height,
        'is_visible': True,
        'content': {'titulo': titulo, 'descripcion': descripcion},
        'styles': {},
        'config': extra_config or {},
    }


def _layout_por_defecto_cartera():
    # `order` es una secuencia global única (1..N), no se reinicia por fila: el frontend
    # (EditableGrid/useDashboardLayout) ordena todos los componentes por este único valor y
    # arma las filas con flex-wrap; `row` es solo informativo/auditoría. Si dos componentes
    # comparten `order`, el orden de renderizado deja de coincidir con el de este listado.
    return [
        _comp('titulo-cartera', DashboardComponent.Tipo.TITLE, 1, 1, 12, 90, 'Cartera con corte al {fecha_corte}'),
        _comp('mensaje-resumen-validacion', DashboardComponent.Tipo.MESSAGE, 2, 2, 12, 110),
        _comp('alerta-sin-fecha', DashboardComponent.Tipo.ALERT, 3, 3, 12, 90),
        _comp('kpi-clientes-unicos', DashboardComponent.Tipo.KPI, 4, 4, 2, 180, 'Clientes únicos'),
        _comp('kpi-cartera-total', DashboardComponent.Tipo.KPI, 4, 5, 2, 180, 'Cartera total'),
        _comp('kpi-cartera-vencida', DashboardComponent.Tipo.KPI, 4, 6, 2, 180, 'Cartera vencida'),
        _comp('kpi-cartera-no-vencida', DashboardComponent.Tipo.KPI, 4, 7, 2, 180, 'Cartera no vencida'),
        _comp('kpi-mayor-120', DashboardComponent.Tipo.KPI, 4, 8, 2, 180, 'Cartera > 120 días'),
        _comp('kpi-mayor-360', DashboardComponent.Tipo.KPI, 4, 9, 2, 180, 'Cartera > 360 días'),
        _comp('panel-filtros', DashboardComponent.Tipo.FILTERS_PANEL, 5, 10, 12, 320, 'Filtros',
              extra_config={'filtros': DEFAULT_FILTROS}),
        _comp('chart-top-clientes', DashboardComponent.Tipo.CHART, 6, 11, 6, 420,
              'Top 10 clientes que más adeudan', 'Ordenado por saldo total descendente. Clic en una barra para ver el detalle.'),
        _comp('chart-cartera-vencida-ciudad', DashboardComponent.Tipo.CHART, 6, 12, 6, 420,
              'Cartera vencida por ciudad'),
        _comp('chart-recuperadores', DashboardComponent.Tipo.CHART, 7, 13, 6, 420,
              'Saldo pendiente por recuperador'),
        _comp('chart-causales', DashboardComponent.Tipo.CHART, 7, 14, 6, 420,
              'Estado general de la cartera por causal', 'Los saldos vacíos se agrupan como SIN GESTIÓN.'),
        _comp('chart-recuperador-causal', DashboardComponent.Tipo.CHART, 8, 15, 12, 440,
              'Causales por recuperador de cartera'),
        _comp('tabla-matriz-recuperador-causal', DashboardComponent.Tipo.TABLE, 9, 16, 12, 420,
              'Matriz de recuperadores y causales'),
        _comp('tabla-detalle', DashboardComponent.Tipo.TABLE, 10, 17, 12, 600,
              'Detalle de documentos'),
    ]


LAYOUTS_POR_DEFECTO = {
    'cartera': _layout_por_defecto_cartera,
}


def componentes_validos(dashboard_id):
    constructor = LAYOUTS_POR_DEFECTO.get(dashboard_id)
    if not constructor:
        raise CarteraError(f'Dashboard "{dashboard_id}" no reconocido.', codigo='DASHBOARD_NO_ENCONTRADO')
    return {c['component_id']: c for c in constructor()}


def obtener_o_crear_layout(dashboard_id):
    layout, creado = DashboardLayout.objects.get_or_create(dashboard_id=dashboard_id)
    if creado:
        _escribir_componentes(layout, componentes_validos(dashboard_id).values())
    return layout


def _escribir_componentes(layout, componentes):
    DashboardComponent.objects.filter(layout=layout).delete()
    objetos = [
        DashboardComponent(
            layout=layout,
            component_id=c['component_id'],
            type=c['type'],
            chart_type=c.get('chart_type', ''),
            row=c['row'],
            order=c['order'],
            width=c['width'],
            height=c['height'],
            is_visible=c.get('is_visible', True),
            content=c.get('content') or {},
            styles=c.get('styles') or {},
            config=c.get('config') or {},
        )
        for c in componentes
    ]
    DashboardComponent.objects.bulk_create(objetos)


def serializar_layout(layout):
    return {
        'dashboard_id': layout.dashboard_id,
        'version': layout.version,
        'scope': layout.scope,
        'theme': layout.theme,
        'components': [
            {
                'component_id': c.component_id,
                'type': c.type,
                'chart_type': c.chart_type,
                'row': c.row,
                'order': c.order,
                'width': c.width,
                'height': c.height,
                'is_visible': c.is_visible,
                'content': c.content,
                'styles': c.styles,
                'config': c.config,
            }
            for c in layout.components.all()
        ],
    }


def _validar_color(valor, campo):
    if not valor:
        return
    if not (_HEX_RE.match(valor) or _RGBA_RE.match(valor)):
        raise CarteraError(f'Color inválido en "{campo}": {valor}', codigo='COLOR_INVALIDO')


_ETIQUETA_HTML_RE = re.compile(r'<[^>]*>')


def _sanitizar_texto(valor, longitud_maxima, campo):
    """Quita únicamente patrones tipo etiqueta HTML (`<script>`, `<img ...>`), no cualquier
    aparición suelta de `<`/`>` — un título legítimo como "Cartera > 120 días" debe sobrevivir."""
    if valor is None:
        return valor
    if not isinstance(valor, str):
        raise CarteraError(f'El campo "{campo}" debe ser texto.', codigo='TEXTO_INVALIDO')
    limpio = _ETIQUETA_HTML_RE.sub('', valor).strip()
    if len(limpio) > longitud_maxima:
        raise CarteraError(f'El campo "{campo}" supera la longitud máxima ({longitud_maxima}).', codigo='TEXTO_DEMASIADO_LARGO')
    return limpio


def validar_componentes(dashboard_id, componentes):
    """Valida y sanitiza la lista de componentes entrante. Lanza CarteraError si algo no es
    válido. Devuelve la lista ya sanitizada, lista para persistir."""
    validos = componentes_validos(dashboard_id)

    if not isinstance(componentes, list) or not componentes:
        raise CarteraError('La configuración debe incluir al menos un componente.', codigo='LAYOUT_VACIO')

    ids_vistos = set()
    resultado = []
    for comp in componentes:
        component_id = comp.get('component_id')
        if component_id not in validos:
            raise CarteraError(f'Componente desconocido: "{component_id}".', codigo='COMPONENTE_NO_PERMITIDO')
        if component_id in ids_vistos:
            raise CarteraError(f'Componente duplicado: "{component_id}".', codigo='COMPONENTE_DUPLICADO')
        ids_vistos.add(component_id)

        definicion = validos[component_id]

        width = comp.get('width', definicion['width'])
        if not isinstance(width, int) or not (ANCHO_MIN <= width <= ANCHO_MAX):
            raise CarteraError(f'Ancho inválido para "{component_id}": {width}.', codigo='ANCHO_INVALIDO')

        height = comp.get('height', definicion['height'])
        if not isinstance(height, int) or not (ALTO_MIN <= height <= ALTO_MAX):
            raise CarteraError(f'Alto inválido para "{component_id}": {height}.', codigo='ALTO_INVALIDO')

        content = dict(comp.get('content') or {})
        if 'titulo' in content:
            content['titulo'] = _sanitizar_texto(content['titulo'], LONGITUD_MAXIMA_TITULO, 'titulo')
        if 'descripcion' in content:
            content['descripcion'] = _sanitizar_texto(content['descripcion'], LONGITUD_MAXIMA_DESCRIPCION, 'descripcion')

        styles = dict(comp.get('styles') or {})
        for campo, valor in styles.items():
            _validar_color(valor, campo)

        resultado.append({
            'component_id': component_id,
            'type': definicion['type'],
            'chart_type': definicion.get('chart_type', ''),
            'row': int(comp.get('row', definicion['row'])),
            'order': int(comp.get('order', definicion['order'])),
            'width': width,
            'height': height,
            'is_visible': bool(comp.get('is_visible', True)),
            'content': content,
            'styles': styles,
            'config': comp.get('config') if comp.get('config') is not None else definicion.get('config', {}),
        })

    return resultado


def _clasificar_cambio(anterior, nuevo):
    cambios = []
    if anterior is None:
        return cambios
    if (anterior['row'], anterior['order']) != (nuevo['row'], nuevo['order']):
        cambios.append(DashboardAuditLog.TipoCambio.ORDEN)
    if (anterior['width'], anterior['height']) != (nuevo['width'], nuevo['height']):
        cambios.append(DashboardAuditLog.TipoCambio.TAMANO)
    if anterior['styles'] != nuevo['styles']:
        cambios.append(DashboardAuditLog.TipoCambio.COLOR)
    if anterior['content'] != nuevo['content']:
        cambios.append(DashboardAuditLog.TipoCambio.TEXTO)
    if anterior['is_visible'] and not nuevo['is_visible']:
        cambios.append(DashboardAuditLog.TipoCambio.OCULTADO)
    return cambios


def aplicar_layout(dashboard_id, componentes_nuevos, changed_by):
    """Persiste el layout validado en una sola operación (sección 9) y registra auditoría por
    cada tipo de cambio detectado por componente (sección 19)."""
    layout = obtener_o_crear_layout(dashboard_id)
    anteriores = {c['component_id']: c for c in serializar_layout(layout)['components']}

    nueva_version = layout.version + 1
    entradas_auditoria = []
    for nuevo in componentes_nuevos:
        anterior = anteriores.get(nuevo['component_id'])
        for tipo_cambio in _clasificar_cambio(anterior, nuevo):
            entradas_auditoria.append(DashboardAuditLog(
                dashboard_id=dashboard_id,
                component_id=nuevo['component_id'],
                change_type=tipo_cambio,
                changed_by=changed_by or 'Anónimo',
                version=nueva_version,
                previous_config=anterior or {},
                new_config=nuevo,
            ))

    _escribir_componentes(layout, componentes_nuevos)
    layout.version = nueva_version
    layout.save(update_fields=['version', 'actualizado_en'])

    if entradas_auditoria:
        DashboardAuditLog.objects.bulk_create(entradas_auditoria)

    return layout


def restablecer_layout(dashboard_id, changed_by):
    layout = obtener_o_crear_layout(dashboard_id)
    componentes_default = list(componentes_validos(dashboard_id).values())

    layout.version += 1
    _escribir_componentes(layout, componentes_default)
    layout.save(update_fields=['version', 'actualizado_en'])

    DashboardAuditLog.objects.create(
        dashboard_id=dashboard_id,
        component_id='',
        change_type=DashboardAuditLog.TipoCambio.RESTABLECIDO,
        changed_by=changed_by or 'Anónimo',
        version=layout.version,
        previous_config={},
        new_config={},
    )
    return layout
