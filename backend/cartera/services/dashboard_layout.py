"""Layout configurable del dashboard (secciones 8, 17, 19, 23 del prompt de personalización).

Cada dashboard nace sin componentes: no hay un layout fijo predefinido por `dashboard_id`. Los
componentes (KPIs y gráficas) se agregan de a uno, cuando el usuario confirma una recomendación
generada a partir de un archivo cargado (`services/generic_charts.py` +
`agregar_componente_generado`, único punto que puede introducir componentes nuevos). La edición
manual del grid (`aplicar_layout`, vía el editor visual) solo puede reordenar/redimensionar/ocultar
/retitular los componentes que YA existen — se valida contra ellos mismos, no contra un catálogo
fijo. Los 16 campos de filtro individuales del pipeline de cartera original quedaron huérfanos
junto con el resto de ese pipeline fijo (ver `docs/integracion/migration_report.md`).
"""

import re

from django.utils.text import slugify

from apps.audit.models import AuditEvent
from apps.audit.services import log_event

from ..constants import PAGE_SIZE_POR_DEFECTO, PAGE_SIZES_PERMITIDOS
from ..exceptions import CarteraError
from ..models import DashboardComponent, DashboardLayout
from .generic_charts import TIPOS_VISUALIZACION

_CHART_TYPES_VALIDOS = {t['id'] for t in TIPOS_VISUALIZACION} | {''}

# Vocabulario de tipos de cambio (antes `DashboardAuditLog.TipoCambio`, hoy valores de `action`
# en `AuditEvent` — Módulo A de "trabajo futuro post-integración": auditoría unificada). Se
# mantienen los mismos literales para que la futura migración de datos históricos
# (docs/audit/unified_audit.md) pueda mapear 1:1 las filas legacy de `DashboardAuditLog`.
class CambioLayout:
    ORDEN = 'CAMBIO_DE_ORDEN'
    TAMANO = 'CAMBIO_DE_TAMANO'
    COLOR = 'CAMBIO_DE_COLOR'
    TEXTO = 'CAMBIO_DE_TEXTO'
    CONFIG = 'CAMBIO_DE_CONFIGURACION'
    OCULTADO = 'COMPONENTE_OCULTADO'
    ELIMINADO = 'COMPONENTE_ELIMINADO'
    RESTABLECIDO = 'DISENO_RESTABLECIDO'

ANCHO_MIN, ANCHO_MAX = 1, 12
ALTO_MIN, ALTO_MAX = 60, 1200
LONGITUD_MAXIMA_TITULO = 200
LONGITUD_MAXIMA_DESCRIPCION = 500

KPI_ANCHO, KPI_ALTO = 3, 180
CHART_ANCHO, CHART_ALTO = 6, 420
TABLA_ALTO = 380

_HEX_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
_RGBA_RE = re.compile(
    r'^rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(,\s*(0|1|0?\.\d+)\s*)?\)$'
)


def componentes_validos(dashboard_id):
    """Los componentes válidos para editar un dashboard son los que YA existen en su layout —
    no hay un catálogo fijo: solo se puede reordenar/redimensionar/ocultar/retitular lo que ya
    fue generado (`establecer_componentes_generados`)."""
    existentes = DashboardComponent.objects.filter(layout__dashboard_id=dashboard_id)
    return {
        c.component_id: {
            'component_id': c.component_id,
            'type': c.type,
            'chart_type': c.chart_type,
            'row': c.row,
            'order': c.order,
            'width': c.width,
            'height': c.height,
            'content': c.content,
            'styles': c.styles,
            'config': c.config,
            'mapeo': c.mapeo,
        }
        for c in existentes
    }


def obtener_o_crear_layout(dashboard_id):
    layout, _creado = DashboardLayout.objects.get_or_create(dashboard_id=dashboard_id)
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
            mapeo=c.get('mapeo') or {},
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
                'mapeo': c.mapeo,
            }
            for c in layout.components.all()
        ],
    }


def _validar_color(valor, campo):
    if not valor:
        return
    if not isinstance(valor, str) or not (_HEX_RE.match(valor) or _RGBA_RE.match(valor)):
        raise CarteraError(f'Color inválido en "{campo}": {valor}', codigo='COLOR_INVALIDO')


# Campos de `styles` que son un mapa {nombre_de_categoria_o_serie: color}, no un color suelto —
# "cada categoría/serie debe tener su propio color editable" (una gráfica de barras/pastel puede
# tener hasta 16 categorías, una agrupada/apilada hasta `MAX_SERIES_EN_GRAFICA` series, así que no
# hay una cantidad fija de campos: el frontend arma un color por cada nombre que trae `content`).
CAMPOS_COLOR_POR_NOMBRE = {'coloresPorCategoria', 'coloresPorSerie'}


def _validar_estilos(styles):
    resultado = {}
    for campo, valor in styles.items():
        if campo in CAMPOS_COLOR_POR_NOMBRE:
            if not isinstance(valor, dict):
                raise CarteraError(f'El campo "{campo}" debe ser un objeto de colores.', codigo='COLOR_INVALIDO')
            mapa = {}
            for nombre, color in valor.items():
                _validar_color(color, f'{campo}.{nombre}')
                if color:
                    mapa[nombre] = color
            resultado[campo] = mapa
        else:
            _validar_color(valor, campo)
            resultado[campo] = valor
    return resultado


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


def _sanitizar_config_paginacion(config):
    """Nunca lanza error: si `allowedPageSizes`/`defaultPageSize` no son válidos, cae al
    valor por defecto (sección 4/5 de la especificación de paginación configurable)."""
    permitidos = [p for p in (config.get('allowedPageSizes') or []) if p in PAGE_SIZES_PERMITIDOS]
    if not permitidos:
        permitidos = sorted(PAGE_SIZES_PERMITIDOS)
    config['allowedPageSizes'] = permitidos

    default_page_size = config.get('defaultPageSize')
    if default_page_size not in permitidos:
        default_page_size = PAGE_SIZE_POR_DEFECTO if PAGE_SIZE_POR_DEFECTO in permitidos else permitidos[0]
    config['defaultPageSize'] = default_page_size

    return config


def validar_componentes(dashboard_id, componentes):
    """Valida y sanitiza la lista de componentes entrante. Lanza CarteraError si algo no es
    válido. Devuelve la lista ya sanitizada, lista para persistir. Una lista vacía es válida: el
    editor visual permite borrar componentes (sección "editor del dashboard"), y borrarlos todos
    deja el dashboard vacío — el mismo estado en el que nace cualquier dashboard nuevo."""
    validos = componentes_validos(dashboard_id)

    if not isinstance(componentes, list):
        raise CarteraError('La configuración debe ser una lista de componentes.', codigo='LAYOUT_INVALIDO')

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

        styles = _validar_estilos(dict(comp.get('styles') or {}))

        config = dict(comp.get('config') if comp.get('config') is not None else definicion.get('config', {}))
        if definicion['type'] == DashboardComponent.Tipo.TABLE:
            config = _sanitizar_config_paginacion(config)

        # A diferencia del resto de campos (siempre se puede editar libremente desde el editor),
        # `chart_type` sí se valida contra el catálogo — un valor arbitrario rompería
        # `GenericChartRenderer` en el frontend (cae al tipo ya guardado, en vez de fallar, si el
        # valor entrante no es uno de los reconocidos).
        chart_type = comp.get('chart_type', definicion.get('chart_type', ''))
        if chart_type not in _CHART_TYPES_VALIDOS:
            chart_type = definicion.get('chart_type', '')

        mapeo = comp.get('mapeo') if comp.get('mapeo') is not None else definicion.get('mapeo', {})
        if not isinstance(mapeo, dict):
            raise CarteraError(f'El campo "mapeo" de "{component_id}" debe ser un objeto.', codigo='MAPEO_INVALIDO')

        resultado.append({
            'component_id': component_id,
            'type': definicion['type'],
            'chart_type': chart_type,
            'row': int(comp.get('row', definicion['row'])),
            'order': int(comp.get('order', definicion['order'])),
            'width': width,
            'height': height,
            'is_visible': bool(comp.get('is_visible', True)),
            'content': content,
            'styles': styles,
            'config': config,
            'mapeo': mapeo,
        })

    return resultado


def _clasificar_cambio(anterior, nuevo):
    cambios = []
    if anterior is None:
        return cambios
    if (anterior['row'], anterior['order']) != (nuevo['row'], nuevo['order']):
        cambios.append(CambioLayout.ORDEN)
    if (anterior['width'], anterior['height']) != (nuevo['width'], nuevo['height']):
        cambios.append(CambioLayout.TAMANO)
    if anterior['styles'] != nuevo['styles']:
        cambios.append(CambioLayout.COLOR)
    if anterior['content'] != nuevo['content']:
        cambios.append(CambioLayout.TEXTO)
    if anterior.get('config') != nuevo.get('config'):
        cambios.append(CambioLayout.CONFIG)
    if anterior.get('chart_type') != nuevo.get('chart_type') or anterior.get('mapeo') != nuevo.get('mapeo'):
        cambios.append(CambioLayout.CONFIG)
    if anterior['is_visible'] and not nuevo['is_visible']:
        cambios.append(CambioLayout.OCULTADO)
    return cambios


def aplicar_layout(dashboard_id, componentes_nuevos, changed_by, actor=None, request=None):
    """Persiste el layout validado en una sola operación (sección 9) y registra auditoría por
    cada tipo de cambio detectado por componente (sección 19) vía el servicio unificado
    `apps.audit.services.log_event` (Módulo A). Un componente existente que no venga incluido en
    `componentes_nuevos` se interpreta como una eliminación (el editor visual borra componentes
    quitándolos del borrador antes de guardar, no hay un endpoint aparte)."""
    layout = obtener_o_crear_layout(dashboard_id)
    anteriores = {c['component_id']: c for c in serializar_layout(layout)['components']}

    nueva_version = layout.version + 1
    ids_nuevos = {nuevo['component_id'] for nuevo in componentes_nuevos}
    cambios_detectados = []
    for nuevo in componentes_nuevos:
        anterior = anteriores.get(nuevo['component_id'])
        for tipo_cambio in _clasificar_cambio(anterior, nuevo):
            cambios_detectados.append((tipo_cambio, nuevo['component_id'], anterior, nuevo))

    for component_id, anterior in anteriores.items():
        if component_id not in ids_nuevos:
            cambios_detectados.append((CambioLayout.ELIMINADO, component_id, anterior, {}))

    _escribir_componentes(layout, componentes_nuevos)
    layout.version = nueva_version
    layout.save(update_fields=['version', 'actualizado_en'])

    for tipo_cambio, component_id, anterior, nuevo in cambios_detectados:
        log_event(
            domain=AuditEvent.Domain.DASHBOARD_LAYOUT, action=tipo_cambio, actor=actor,
            dashboard_id=dashboard_id, component_id=component_id,
            previous_values=anterior or {}, new_values=nuevo,
            metadata={'version': nueva_version, 'changed_by_label': changed_by or 'Anónimo'},
            request=request,
        )

    return layout


def restablecer_layout(dashboard_id, changed_by, actor=None, request=None):
    """"Restablecer" ya no regenera un layout fijo (no existe uno): vuelve a mostrar cualquier
    componente que se haya ocultado, sin alterar su posición/tamaño/título. Para regenerar las
    gráficas desde cero hay que cargar un archivo nuevo (`establecer_componentes_generados`)."""
    layout = obtener_o_crear_layout(dashboard_id)
    componentes = list(componentes_validos(dashboard_id).values())
    for componente in componentes:
        componente['is_visible'] = True

    layout.version += 1
    _escribir_componentes(layout, componentes)
    layout.save(update_fields=['version', 'actualizado_en'])

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action=CambioLayout.RESTABLECIDO, actor=actor,
        dashboard_id=dashboard_id, metadata={'version': layout.version, 'changed_by_label': changed_by or 'Anónimo'},
        request=request,
    )
    return layout


# Tipos de visualización que dibujan una leyenda (varias series o porciones) — los únicos donde
# tiene sentido ofrecer "posición de la leyenda" en el panel de propiedades. Las gráficas de una
# sola serie (barras simples, líneas) no tienen nada que distinguir en una leyenda.
TIPOS_CON_LEYENDA = {'barras_agrupadas', 'barras_apiladas', 'area_apilada', 'lineas_multiples', 'pastel', 'dona'}
LEYENDA_POSICION_POR_DEFECTO = 'abajo'


def _generar_component_id_unico(titulo, usados):
    base = slugify(titulo)[:80] or 'grafica'
    candidato = base
    sufijo = 2
    while candidato in usados:
        candidato = f'{base}-{sufijo}'
        sufijo += 1
    usados.add(candidato)
    return candidato


def agregar_componente_generado(dashboard_id, especificacion, reemplazar_existentes=False, actor=None, request=None):
    """Agrega UNA gráfica/KPI/tabla generado a partir de una recomendación confirmada por el
    usuario (`generic_charts.py::generar_recomendaciones` + `generar_datos_grafica`) o de un
    componente armado a mano para la Zona Personal (`views.py::AgregarGraficaView`) — único punto
    que puede introducir componentes nuevos (su `component_id` se deriva del título, no de un
    catálogo fijo). Por defecto se suma al resto de componentes ya existentes (el usuario va
    agregando gráficas de a una desde la lista de recomendaciones); `reemplazar_existentes=True`
    empieza de cero primero (se usa en la primera gráfica que se agrega tras cargar un archivo
    nuevo, para no mezclar datos de dos archivos distintos en el mismo dashboard).

    `especificacion` es `{'titulo', 'descripcion', 'columna_valor', 'columna_categoria',
    'columna_serie', 'columna_valor_y', 'columna_id', 'columnas_valor', 'tipo_visualizacion',
    'ancho_columnas', 'zona', 'datos'}`, donde `datos` ya viene calculado por
    `generic_charts.generar_datos_grafica`/`generar_datos_multiserie`/`generar_datos_multivalor`/
    `generar_datos_dispersion`/`generar_datos_tabla` — su forma (`datos['tipo']` =
    'kpi'/'chart'/'multiserie'/'dispersion'/'tabla_multi') decide qué se guarda en `content`;
    `tipo_visualizacion` (una de `generic_charts.TIPOS_VISUALIZACION`, p. ej. 'barras_verticales',
    'lineas', 'pastel', 'dona', 'barras_agrupadas', 'barras_apiladas') solo decide CÓMO se dibuja
    esa misma información — el frontend la usa para elegir el componente de renderizado.
    `ancho_columnas` (1, 2 o 4 — cantidad de columnas del grid de 12 que ocupa cada componente, no
    de `columnas_valor`) traduce a `width = 12 // ancho_columnas`; si no viene, se mantiene el
    ancho por defecto histórico (`KPI_ANCHO`/`CHART_ANCHO`), usado por el flujo legado de
    recomendaciones automáticas. `zona`, si viene, se guarda en `config['zona']` — así lo
    reconocen `EditableGrid.jsx` (agrupación visual en modo edición) y `plantilla._escribir_plantilla`
    (preservación al reaplicar el mapeo de las 15 posiciones fijas). Todo componente generado trae
    una descripción de partida (editable después desde el panel de propiedades, igual que el
    título) y, si su tipo dibuja una leyenda, una posición por defecto también editable ahí."""
    layout = obtener_o_crear_layout(dashboard_id)

    existentes = [] if reemplazar_existentes else list(componentes_validos(dashboard_id).values())
    usados = {c['component_id'] for c in existentes}

    titulo = especificacion['titulo']
    descripcion = especificacion.get('descripcion') or ''
    datos = especificacion['datos']
    component_id = _generar_component_id_unico(titulo, usados)
    orden = len(existentes) + 1
    ancho_elegido = especificacion.get('ancho_columnas')
    kpi_ancho = (12 // ancho_elegido) if ancho_elegido else KPI_ANCHO
    chart_ancho = (12 // ancho_elegido) if ancho_elegido else CHART_ANCHO
    config = {
        'columna_valor': especificacion.get('columna_valor'),
        'columna_categoria': especificacion.get('columna_categoria') or None,
        'columna_serie': especificacion.get('columna_serie') or None,
    }
    zona = especificacion.get('zona')
    if zona:
        config['zona'] = zona

    if datos['tipo'] == 'dispersion':
        config['columna_valor_y'] = especificacion.get('columna_valor_y')
        nuevo = {
            'component_id': component_id, 'type': DashboardComponent.Tipo.CHART, 'chart_type': 'dispersion',
            'row': orden, 'order': orden, 'width': chart_ancho, 'height': CHART_ALTO, 'is_visible': True,
            'content': {'titulo': titulo, 'descripcion': descripcion, 'puntos': datos['puntos']},
            'styles': {}, 'config': config,
        }
    elif datos['tipo'] == 'kpi':
        nuevo = {
            'component_id': component_id, 'type': DashboardComponent.Tipo.KPI, 'chart_type': '',
            'row': orden, 'order': orden, 'width': kpi_ancho, 'height': KPI_ALTO, 'is_visible': True,
            'content': {'titulo': titulo, 'descripcion': descripcion, 'valor': datos['valor']},
            'styles': {}, 'config': config,
        }
    elif datos['tipo'] == 'tabla_multi':
        config['columna_id'] = especificacion.get('columna_id')
        config['columnas_valor'] = especificacion.get('columnas_valor')
        nuevo = {
            'component_id': component_id, 'type': DashboardComponent.Tipo.CHART, 'chart_type': 'tabla',
            'row': orden, 'order': orden, 'width': chart_ancho, 'height': TABLA_ALTO, 'is_visible': True,
            'content': {
                'titulo': titulo, 'descripcion': descripcion,
                'columnas': datos['columnas'], 'filas': datos['filas'], 'total': datos['total'],
            },
            'styles': {}, 'config': config,
        }
    elif datos['tipo'] == 'multiserie':
        if especificacion.get('columnas_valor'):
            config['columnas_valor'] = especificacion['columnas_valor']
        chart_type = especificacion.get('tipo_visualizacion') or 'barras_agrupadas'
        if chart_type in TIPOS_CON_LEYENDA:
            config['leyenda_posicion'] = LEYENDA_POSICION_POR_DEFECTO
        nuevo = {
            'component_id': component_id, 'type': DashboardComponent.Tipo.CHART, 'chart_type': chart_type,
            'row': orden, 'order': orden, 'width': chart_ancho, 'height': CHART_ALTO, 'is_visible': True,
            'content': {'titulo': titulo, 'descripcion': descripcion, 'categorias': datos['categorias'], 'series': datos['series']},
            'styles': {}, 'config': config,
        }
    else:
        chart_type = especificacion.get('tipo_visualizacion') or 'barras_horizontales'
        if chart_type in TIPOS_CON_LEYENDA:
            config['leyenda_posicion'] = LEYENDA_POSICION_POR_DEFECTO
        nuevo = {
            'component_id': component_id, 'type': DashboardComponent.Tipo.CHART, 'chart_type': chart_type,
            'row': orden, 'order': orden, 'width': chart_ancho, 'height': CHART_ALTO, 'is_visible': True,
            'content': {'titulo': titulo, 'descripcion': descripcion, 'categorias': datos['categorias'], 'valores': datos['valores']},
            'styles': {}, 'config': config,
        }

    _escribir_componentes(layout, existentes + [nuevo])
    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_CHART_ADDED', actor=actor,
        dashboard_id=dashboard_id, component_id=component_id, new_values=nuevo,
        metadata={'version': layout.version, 'reemplazo_existentes': reemplazar_existentes},
        request=request,
    )
    return layout


PRESENTACIONAL_ALTO = {DashboardComponent.Tipo.TITLE: 70, DashboardComponent.Tipo.TEXT: 40}
PRESENTACIONAL_ANCHO_DEFECTO = 12
_TITULOS_BASE_PRESENTACIONAL = {DashboardComponent.Tipo.TITLE: 'Nuevo título', DashboardComponent.Tipo.TEXT: 'Separador'}


def agregar_componente_presentacional(dashboard_id, tipo, ancho_columnas=None, zona=None, actor=None, request=None):
    """Agrega un componente puramente presentacional (título o separador, panel lateral de
    componentes del editor de dashboard) — a diferencia de `agregar_componente_generado`, no
    depende de ningún archivo/carga ni calcula nada a partir de columnas: nace con un valor por
    defecto en `content.titulo` (vacío para el separador, un texto de partida para el título),
    editable después desde el panel de propiedades — ya genérico para cualquier componente
    (`content.titulo`/`descripcion`), sin necesitar ningún caso especial ahí. `zona`, si viene, se
    guarda en `config['zona']` (p. ej. `'personal'`, para que `EditableGrid.jsx` lo agrupe junto
    al resto de la Zona Personal, igual que ya hace `agregar_componente_generado`)."""
    if tipo not in PRESENTACIONAL_ALTO:
        raise CarteraError(f'Tipo de componente presentacional inválido: "{tipo}".', codigo='TIPO_INVALIDO')

    layout = obtener_o_crear_layout(dashboard_id)
    existentes = list(componentes_validos(dashboard_id).values())
    usados = {c['component_id'] for c in existentes}

    titulo_base = _TITULOS_BASE_PRESENTACIONAL[tipo]
    component_id = _generar_component_id_unico(titulo_base, usados)
    orden = len(existentes) + 1
    ancho = (12 // ancho_columnas) if ancho_columnas else PRESENTACIONAL_ANCHO_DEFECTO
    config = {'zona': zona} if zona else {}
    nuevo = {
        'component_id': component_id, 'type': tipo, 'chart_type': '',
        'row': orden, 'order': orden, 'width': ancho, 'height': PRESENTACIONAL_ALTO[tipo], 'is_visible': True,
        'content': {'titulo': titulo_base if tipo == DashboardComponent.Tipo.TITLE else ''},
        'styles': {}, 'config': config,
    }

    _escribir_componentes(layout, existentes + [nuevo])
    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])

    log_event(
        domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_CHART_ADDED', actor=actor,
        dashboard_id=dashboard_id, component_id=component_id, new_values=nuevo,
        metadata={'version': layout.version}, request=request,
    )
    return layout
