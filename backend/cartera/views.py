import logging
import os
import uuid

import pandas as pd
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from . import permisos
from .constants import PAGE_SIZE_POR_DEFECTO, PAGE_SIZES_PERMITIDOS
from .exceptions import CarteraError
from .models import CargaArchivo, RegistroCartera
from .services import (
    aggregations, column_mapper, dashboard_layout, export_service, excel_reader, filters,
    generic_charts, historico, ingest, plantilla,
)
from .services.calculator import anotar_estado_y_mora, resumen_kpis
from .utils.dates import fecha_corte_por_defecto, parse_fecha

logger = logging.getLogger(__name__)


def _acceso_denegado():
    return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para acceder a este dashboard.'}, status=403)


def _tiene_acceso(request, dashboard_id, *, requiere_edicion=False):
    """Todos los endpoints de datos de cartera de este archivo comparten el mismo permiso global
    de respaldo (`dashboard.view` — no existe un permiso "editar datos" separado del catálogo,
    quien puede ver el dashboard puede cargar/consultar/exportar sus datos), pero ahora también
    respetan el control de acceso por dashboard (roles editores/lectores + dueño,
    `permisos.tiene_acceso_dashboard`) cuando el dashboard de la carga tiene una ACL propia
    configurada."""
    return permisos.tiene_acceso_dashboard(
        request, dashboard_id, permiso_global=permisos.DASHBOARD_VIEW, requiere_edicion=requiere_edicion,
    )

CAMPOS_VALUES = [
    'cliente', 'ruc_cliente', 'codigo_cliente', 'identificador_cliente', 'sucursal', 'ciudad',
    'zona', 'vendedor_ejecutivo', 'estado_cliente', 'telefono', 'direccion', 'numero_documento',
    'fecha_emision', 'fecha_vencimiento', 'saldo', 'articulo', 'vence_original', 'observacion',
    'mes', 'tipo_venta', 'causal', 'producto', 'fecha_compromiso_pago', 'observaciones',
    'tipo_cartera', 'recuperador', 'dias_credito',
]


def _sanitizar_nombre_original(nombre):
    base = os.path.basename(nombre or 'archivo')
    return base[:255]


def _resolver_fecha_corte(request, carga):
    crudo = request.query_params.get('fecha_corte') if hasattr(request, 'query_params') else None
    if crudo:
        fecha = parse_fecha(crudo)
        if fecha:
            return fecha
    if carga.fecha_corte:
        return carga.fecha_corte
    return fecha_corte_por_defecto()


def _dataframe_de_carga(carga, request):
    queryset = RegistroCartera.objects.filter(carga_id=carga.id)
    queryset = filters.aplicar_filtros_queryset(queryset, request.query_params)
    valores = list(queryset.values(*CAMPOS_VALUES))
    if valores:
        df = pd.DataFrame(valores)
        df['saldo'] = df['saldo'].astype(float)
    else:
        df = pd.DataFrame(columns=CAMPOS_VALUES)
    return df


def _df_anotado_y_filtrado(carga, request):
    fecha_corte = _resolver_fecha_corte(request, carga)
    df = _dataframe_de_carga(carga, request)
    df = anotar_estado_y_mora(df, fecha_corte)
    df = filters.aplicar_filtros_dataframe(df, request.query_params)
    return df, fecha_corte


class ValidarArchivoView(APIView):
    def post(self, request):
        dashboard_id = (request.data.get('dashboard_id') or 'cartera').strip() or 'cartera'
        if not _tiene_acceso(request, dashboard_id, requiere_edicion=True):
            return _acceso_denegado()

        archivo = request.FILES.get('archivo')
        if archivo is None:
            raise CarteraError('No se recibió ningún archivo.', codigo='ARCHIVO_REQUERIDO')

        if archivo.size > settings.UPLOAD_MAX_SIZE_BYTES:
            raise CarteraError(
                f'El archivo supera el tamaño máximo permitido ({settings.UPLOAD_MAX_SIZE_BYTES} bytes).',
                codigo='ARCHIVO_DEMASIADO_GRANDE',
            )

        contenido = archivo.read()
        nombre_original = _sanitizar_nombre_original(archivo.name)
        excel_reader.validar_extension_y_firma(nombre_original, contenido)

        _, extension = os.path.splitext(nombre_original.lower())
        nombre_temp = f'{uuid.uuid4().hex}{extension}'
        ruta_temp = settings.CARTERA_TEMP_UPLOADS_DIR / nombre_temp
        with open(ruta_temp, 'wb') as f:
            f.write(contenido)

        try:
            hojas = excel_reader.listar_hojas(str(ruta_temp))
            hoja_solicitada = request.data.get('hoja')
            hoja = hoja_solicitada if hoja_solicitada in hojas else hojas[0]
            df = excel_reader.leer_hoja(str(ruta_temp), hoja)
        except CarteraError:
            os.remove(ruta_temp)
            raise

        mapeo_sugerido = column_mapper.detectar_mapeo(df.columns.tolist())
        preview = excel_reader.preview_hoja(df, 20)

        carga = CargaArchivo.objects.create(
            dashboard_id=dashboard_id,
            subido_por=request.user,
            nombre_original=nombre_original,
            nombre_hoja=hoja,
            tamano_bytes=archivo.size,
            estado=CargaArchivo.Estado.VALIDADO,
            total_filas_excel=len(df),
            archivo_temp_nombre=nombre_temp,
        )

        return Response({
            'carga_id': str(carga.id),
            'dashboard_id': carga.dashboard_id,
            'columnas_detectadas': df.columns.tolist(),
            'nombre_archivo': nombre_original,
            'tamano_bytes': archivo.size,
            'fecha_carga': carga.fecha_carga.isoformat(),
            'hojas_disponibles': hojas,
            'hoja_seleccionada': hoja,
            'total_filas_detectadas': len(df),
            'mapeo_sugerido': mapeo_sugerido,
            'preview': preview,
        }, status=200)


_HOJA_ARCHIVO_PERMANENTE = 'Datos'


def _leer_archivo_temporal_de_carga(carga):
    """Lee el archivo de una carga — preferentemente su copia permanente
    (`archivo_permanente_nombre`, escrita al aplicar la plantilla, nunca se limpia
    automáticamente) para que el mapeo de columnas se pueda seguir ajustando mucho después de
    subir el archivo; si todavía no se aplicó ningún mapeo, cae al archivo temporal (se limpia a
    las 24h, `clean_temp_uploads`)."""
    if carga.archivo_permanente_nombre:
        ruta = settings.CARTERA_ARCHIVOS_DIR / carga.archivo_permanente_nombre
        return ruta, excel_reader.leer_hoja(str(ruta), _HOJA_ARCHIVO_PERMANENTE)
    if not carga.archivo_temp_nombre:
        raise CarteraError('El archivo temporal ya no está disponible; vuelve a cargarlo.', codigo='ARCHIVO_NO_DISPONIBLE')
    ruta_temp = settings.CARTERA_TEMP_UPLOADS_DIR / carga.archivo_temp_nombre
    return ruta_temp, excel_reader.leer_hoja(str(ruta_temp), carga.nombre_hoja)


def _guardar_archivo_permanente(carga, df):
    """Copia el archivo (ya renombrado por alias) a `CARTERA_ARCHIVOS_DIR` — se llama al aplicar
    la plantilla, para que el archivo real siga disponible después de que se limpie el temporal
    (`clean_temp_uploads`) y así se pueda reconfigurar el mapeo de un componente más adelante
    desde "Configurar componente" sin volver a cargar el archivo."""
    nombre_permanente = f'{carga.id}.xlsx'
    ruta = settings.CARTERA_ARCHIVOS_DIR / nombre_permanente
    df.to_excel(ruta, index=False, sheet_name=_HOJA_ARCHIVO_PERMANENTE)
    carga.archivo_permanente_nombre = nombre_permanente
    carga.save(update_fields=['archivo_permanente_nombre'])


def _aplicar_alias_columnas(df, aliases):
    """Renombra las columnas del archivo según el alias que haya elegido el usuario en el paso
    "renombrar columnas" (nombre original -> nuevo nombre); a partir de acá todo el resto del
    flujo (análisis, mapeo, cálculo de datos, títulos/descripciones generados) usa el nombre
    nuevo como si fuera el original. Una columna sin alias (o con alias igual al original) no se
    toca. Dos columnas que terminen con el mismo nombre son un error del usuario, no un caso a
    resolver en silencio: con nombres duplicados, `df[nombre]` deja de devolver una única serie."""
    if not aliases:
        return df
    mapa = {
        original: str(nuevo).strip()
        for original, nuevo in aliases.items()
        if original in df.columns and str(nuevo or '').strip() and str(nuevo).strip() != original
    }
    if not mapa:
        return df
    resultado = [mapa.get(c, c) for c in df.columns]
    if len(set(resultado)) != len(resultado):
        raise CarteraError('Dos o más columnas quedarían con el mismo nombre después de renombrar.', codigo='ALIAS_DUPLICADO')
    return df.rename(columns=mapa)


def _aplicar_valores_blancos(df, valores_blancos):
    """Reemplaza los valores en blanco (NaN) de las columnas que el usuario eligió en el paso
    "valores en blanco" (nombre de columna ya renombrado -> valor de reemplazo, ver
    `generic_charts.columnas_con_blancos_recurrentes` y el paso `VALORES_EN_BLANCO` del asistente
    de carga) — a partir de acá el resto del flujo (análisis, mapeo, cálculo de datos, histórico)
    ve esas celdas como si el archivo original las hubiera traído completas. Una columna sin valor
    elegido (o con un valor vacío) no se toca: sus blancos siguen el tratamiento normal
    (`services/generic_charts.py` — agrupados como "Sin dato" o ignorados en el cálculo, según se
    use como categoría o como valor)."""
    if not valores_blancos:
        return df
    df = df.copy()
    for columna, valor in valores_blancos.items():
        valor = str(valor).strip() if valor is not None else ''
        if columna in df.columns and valor:
            df[columna] = df[columna].fillna(valor)
    return df


class AnalizarColumnasView(APIView):
    """`POST /api/cartera/analizar-columnas` — analiza las columnas de un archivo ya subido
    (`carga_id`, ver `ValidarArchivoView`) y devuelve cuáles son aptas para generar una gráfica
    (columnas de valor numéricas, columnas de categoría para agrupar), sin asumir ningún esquema
    de negocio fijo (`services/generic_charts.py`)."""

    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        _ruta_temp, df = _leer_archivo_temporal_de_carga(carga)

        return Response({'carga_id': str(carga.id), **generic_charts.analizar_columnas(df)})


class RecomendarGraficasView(APIView):
    """`POST /api/cartera/recomendar-graficas` — a partir de las columnas ya analizadas
    (`AnalizarColumnasView`) y de cuáles marcó el usuario como utilizables (`columnas_utilizables`
    — el análisis automático es solo una sugerencia, nunca excluye una columna por sí solo),
    propone qué gráficas armar: un KPI de total por cada columna numérica marcada y una gráfica de
    barras por cada combinación razonable de valor × categoría entre las marcadas
    (`services/generic_charts.py::generar_recomendaciones`). También calcula de una vez los datos
    de cada recomendación (`calcular_datos_recomendaciones`) para que el frontend pueda mostrar
    una vista previa real de todas, sin una solicitud aparte por cada una — todavía no persiste
    nada, eso ocurre al confirmar una recomendación (`AgregarGraficaView`)."""

    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        _ruta_temp, df = _leer_archivo_temporal_de_carga(carga)

        analisis = generic_charts.analizar_columnas(df)
        columnas = analisis['columnas']

        columnas_utilizables = request.data.get('columnas_utilizables')
        if columnas_utilizables is not None:
            columnas = generic_charts.aplicar_seleccion_usuario(columnas, columnas_utilizables)

        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        recomendaciones = generic_charts.calcular_datos_recomendaciones(df, recomendaciones)
        return Response({'carga_id': str(carga.id), 'recomendaciones': recomendaciones})


_TIPOS_QUE_REQUIEREN_SERIE = {t['id'] for t in generic_charts.TIPOS_VISUALIZACION if t['requiere_serie']}


_ANCHOS_COLUMNAS_VALIDOS = (1, 2, 4)


class AgregarGraficaView(APIView):
    """`POST /api/cartera/agregar-grafica` — confirma UNA recomendación (o una gráfica armada a
    mano con las mismas columnas), en cualquiera de sus formas de visualización disponibles
    (`tipo_visualizacion`, uno de `generic_charts.TIPOS_VISUALIZACION`): calcula sus datos y la
    agrega al dashboard de la carga (`services/dashboard_layout.py::agregar_componente_generado`).
    `reemplazar_existentes` limpia el dashboard antes de agregar (se usa en la primera gráfica que
    se confirma tras cargar un archivo nuevo, para no mezclar datos de dos archivos).

    `calculo` (opcional, uno de 'kpi'/'chart'/'multivalor'/'multiserie'/'dispersion'/'tabla') es
    lo que usa la "Zona Personal" del editor de dashboard (`AgregarComponentePersonalModal.jsx`)
    para elegir explícitamente qué calcular, con los mismos selectores que ya arma
    `SlotFields.jsx::camposParaSlot` para las 15 posiciones fijas — cuando viene, decide la rama
    de cálculo sin ambigüedad. Si no viene (flujo legado de recomendaciones automáticas), se
    conserva la inferencia histórica por `tipo_visualizacion`. `ancho_columnas` (1, 2 o 4) y
    `zona` ('personal' para la Zona Personal) se reenvían tal cual a
    `agregar_componente_generado`."""

    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        titulo = (request.data.get('titulo') or '').strip()
        descripcion = (request.data.get('descripcion') or '').strip()
        calculo = request.data.get('calculo') or None
        columna_valor = request.data.get('columna_valor')
        columna_categoria = request.data.get('columna_categoria') or None
        columna_serie = request.data.get('columna_serie') or None
        columna_valor_y = request.data.get('columna_valor_y') or None
        columna_id = request.data.get('columna_id') or None
        columnas_valor = request.data.get('columnas_valor') or None
        tipo_agregacion = request.data.get('tipo_agregacion') or None
        tipo_visualizacion = request.data.get('tipo_visualizacion') or None
        ancho_columnas = request.data.get('ancho_columnas') or None
        zona = request.data.get('zona') or None
        if not titulo:
            raise CarteraError('La gráfica necesita un título.', codigo='TITULO_REQUERIDO')
        if calculo not in ('tabla', 'multivalor') and not columna_valor:
            raise CarteraError('La gráfica necesita una columna de valor.', codigo='COLUMNA_VALOR_REQUERIDA')
        if ancho_columnas is not None and ancho_columnas not in _ANCHOS_COLUMNAS_VALIDOS:
            raise CarteraError('ancho_columnas debe ser 1, 2 o 4.', codigo='ANCHO_COLUMNAS_INVALIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id, requiere_edicion=True):
            return _acceso_denegado()
        _ruta_temp, df = _leer_archivo_temporal_de_carga(carga)

        if calculo == 'tabla':
            if not columna_id or not columnas_valor:
                raise CarteraError(
                    'La tabla necesita una identidad de fila y al menos una columna de valor.', codigo='COLUMNA_VALOR_REQUERIDA',
                )
            datos = generic_charts.generar_datos_tabla(df, columna_id, columnas_valor)
        elif calculo == 'multivalor':
            if not columna_categoria or not columnas_valor or len(columnas_valor) < 2:
                raise CarteraError(
                    'Esta visualización necesita una categoría y 2 o más columnas de valor.', codigo='COLUMNAS_VALOR_REQUERIDAS',
                )
            datos = generic_charts.generar_datos_multivalor(df, columna_categoria, columnas_valor)
        elif calculo == 'kpi' or (calculo is None and tipo_visualizacion == 'kpi'):
            if tipo_agregacion == 'conteo_unicos':
                datos = generic_charts.generar_conteo_valores_unicos(df, columna_valor)
            elif tipo_agregacion == 'promedio':
                datos = generic_charts.generar_promedio_columna(df, columna_valor)
            else:
                datos = generic_charts.generar_datos_grafica(df, columna_valor, None)
        elif calculo == 'dispersion' or (calculo is None and tipo_visualizacion == 'dispersion'):
            if not columna_valor_y:
                raise CarteraError(
                    'Esta visualización necesita una segunda columna numérica.', codigo='COLUMNA_VALOR_Y_REQUERIDA',
                )
            datos = generic_charts.generar_datos_dispersion(df, columna_valor, columna_valor_y)
        elif calculo == 'multiserie' or (calculo is None and tipo_visualizacion in _TIPOS_QUE_REQUIEREN_SERIE):
            if not columna_serie:
                raise CarteraError(
                    'Esta visualización necesita una segunda columna de agrupación.', codigo='COLUMNA_SERIE_REQUERIDA',
                )
            datos = generic_charts.generar_datos_multiserie(df, columna_valor, columna_categoria, columna_serie)
        else:
            datos = generic_charts.generar_datos_grafica(df, columna_valor, columna_categoria)

        if datos is None:
            raise CarteraError(f'La columna elegida para "{titulo}" ya no existe en el archivo.', codigo='COLUMNA_INVALIDA')

        layout = dashboard_layout.agregar_componente_generado(
            carga.dashboard_id,
            {
                'titulo': titulo, 'descripcion': descripcion, 'columna_valor': columna_valor,
                'columna_categoria': columna_categoria, 'columna_serie': columna_serie,
                'columna_valor_y': columna_valor_y, 'columna_id': columna_id, 'columnas_valor': columnas_valor,
                'tipo_visualizacion': tipo_visualizacion, 'ancho_columnas': ancho_columnas, 'zona': zona,
                'datos': datos,
            },
            reemplazar_existentes=bool(request.data.get('reemplazar_existentes')),
            actor=request.user, request=request,
        )

        if carga.estado != CargaArchivo.Estado.PROCESADO:
            carga.estado = CargaArchivo.Estado.PROCESADO
            carga.save(update_fields=['estado'])

        return Response(dashboard_layout.serializar_layout(layout), status=201)


class ArchivoActualDashboardView(APIView):
    """`POST /api/cartera/plantilla/archivo-actual` — el archivo (permanente) que alimenta
    actualmente un dashboard, si ya se le aplicó alguno: la última `CargaArchivo` PROCESADA con
    copia permanente para ese `dashboard_id`. Lo usa "Configurar componente" (editor de
    dashboard) para poder reconfigurar el mapeo de columnas de UN componente ya existente sin
    tener que volver a cargar el archivo. `disponible=False` (no un error) cuando el dashboard
    todavía no tiene ningún archivo real aplicado (solo datos ficticios de la plantilla)."""

    def post(self, request):
        dashboard_id = request.data.get('dashboard_id')
        if not dashboard_id:
            raise CarteraError('dashboard_id es requerido.', codigo='DASHBOARD_ID_REQUERIDO')
        if not _tiene_acceso(request, dashboard_id):
            return _acceso_denegado()

        carga = CargaArchivo.objects.filter(
            dashboard_id=dashboard_id, estado=CargaArchivo.Estado.PROCESADO,
        ).exclude(archivo_permanente_nombre='').order_by('-fecha_carga').first()

        if not carga:
            return Response({'disponible': False})

        _ruta, df = _leer_archivo_temporal_de_carga(carga)
        analisis = generic_charts.analizar_columnas(df)
        return Response({
            'disponible': True, 'carga_id': str(carga.id), 'nombre_archivo': carga.nombre_original,
            'total_filas': len(df), 'columnas': analisis['columnas'],
        })


class SugerirMapeoPlantillaView(APIView):
    """`POST /api/cartera/plantilla/sugerir` — a partir de un archivo ya subido, analiza sus
    columnas y propone qué columna(s) usar para cada una de las 15 posiciones fijas de la
    plantilla (`services/plantilla.py::sugerir_mapeo`), junto con una vista previa real de los
    datos que resultarían (`calcular_datos_mapeo`) — todavía no persiste nada, eso ocurre al
    confirmar el mapeo (`AplicarMapeoPlantillaView`). `aliases` (opcional, del paso "renombrar
    columnas") renombra el archivo antes de analizarlo. También es el primer punto del flujo con
    cada columna ya clasificada (apta para valor/categoría), así que de acá sale
    `columnas_con_blancos` (`generic_charts.columnas_con_blancos_recurrentes`): las columnas con
    valores en blanco recurrentes, para que el frontend avise cómo se van a tratar."""

    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        _ruta_temp, df = _leer_archivo_temporal_de_carga(carga)
        df = _aplicar_alias_columnas(df, request.data.get('aliases'))
        df = _aplicar_valores_blancos(df, request.data.get('valores_blancos'))

        analisis = generic_charts.analizar_columnas(df)
        mapeo = plantilla.sugerir_mapeo(analisis['columnas'])
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        columnas_con_blancos = generic_charts.columnas_con_blancos_recurrentes(df)

        return Response({
            'carga_id': str(carga.id), 'columnas': analisis['columnas'], 'mapeo': mapeo, 'datos': datos,
            'columnas_con_blancos': columnas_con_blancos,
        })


class PrevisualizarMapeoPlantillaView(APIView):
    """`POST /api/cartera/plantilla/previsualizar` — recalcula los datos de las 13 posiciones a
    partir de un mapeo ya ajustado a mano por el usuario (sin persistir nada), para que el panel
    de mapeo se actualice en tiempo real cada vez que cambia un selector de columna, sin esperar
    a "Aplicar a la plantilla". Recibe el mismo `aliases` que `SugerirMapeoPlantillaView` para que
    el mapeo (armado sobre los nombres ya renombrados) siga resolviendo contra las mismas
    columnas."""

    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        mapeo = request.data.get('mapeo')
        if not isinstance(mapeo, dict):
            raise CarteraError('mapeo es requerido.', codigo='MAPEO_REQUERIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        _ruta_temp, df = _leer_archivo_temporal_de_carga(carga)
        df = _aplicar_alias_columnas(df, request.data.get('aliases'))
        df = _aplicar_valores_blancos(df, request.data.get('valores_blancos'))

        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        return Response({'carga_id': str(carga.id), 'datos': datos})


class ValoresColumnaPlantillaView(APIView):
    """`POST /api/cartera/plantilla/valores-columna` — valores distintos de una columna del
    archivo (`carga_id`, `columna`, con el mismo `aliases` del resto del flujo), para poblar el
    selector "valor" del filtro opcional de una posición (`columna_filtro`/`valor_filtro` en el
    mapeo — ver `services/plantilla.py::_aplicar_filtro_slot`)."""

    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        columna = request.data.get('columna')
        if not columna:
            raise CarteraError('columna es requerida.', codigo='COLUMNA_REQUERIDA')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        _ruta_temp, df = _leer_archivo_temporal_de_carga(carga)
        df = _aplicar_alias_columnas(df, request.data.get('aliases'))
        df = _aplicar_valores_blancos(df, request.data.get('valores_blancos'))

        resultado = generic_charts.valores_unicos_de_columna(df, columna)
        if resultado is None:
            raise CarteraError('La columna elegida ya no existe en el archivo.', codigo='COLUMNA_INVALIDA')

        return Response({'carga_id': str(carga.id), **resultado})


class AplicarMapeoPlantillaView(APIView):
    """`POST /api/cartera/plantilla/aplicar` — confirma (con los ajustes que haya hecho el
    usuario) el mapeo propuesto por `SugerirMapeoPlantillaView` y sobreescribe las 15 posiciones
    del dashboard con los datos reales resultantes (`services/plantilla.py::aplicar_mapeo`).
    Recibe el mismo `aliases` que el resto del flujo de mapeo. `columnas_historicas` (nombres ya
    renombrados, del paso "Renombrar columnas") reemplaza la configuración persistente de columnas
    históricas del dashboard (`historico.establecer_columnas_historicas`) y decide qué columnas se
    guardan en `FilaArchivoHistorico` para esta carga (`historico.guardar_filas_historicas`) — solo
    esas, no la fila completa."""

    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        mapeo = request.data.get('mapeo')
        if not isinstance(mapeo, dict):
            raise CarteraError('mapeo es requerido.', codigo='MAPEO_REQUERIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id, requiere_edicion=True):
            return _acceso_denegado()
        _ruta_temp, df = _leer_archivo_temporal_de_carga(carga)
        df = _aplicar_alias_columnas(df, request.data.get('aliases'))
        df = _aplicar_valores_blancos(df, request.data.get('valores_blancos'))

        columnas_historicas = request.data.get('columnas_historicas') or []

        layout = plantilla.aplicar_mapeo(carga.dashboard_id, df, mapeo, actor=request.user, request=request)
        _guardar_archivo_permanente(carga, df)
        historico.establecer_columnas_historicas(carga.dashboard_id, columnas_historicas)
        historico.guardar_filas_historicas(carga, df, columnas_historicas)

        if carga.estado != CargaArchivo.Estado.PROCESADO:
            carga.estado = CargaArchivo.Estado.PROCESADO
            carga.save(update_fields=['estado'])

        return Response(dashboard_layout.serializar_layout(layout), status=200)


class ProcesarView(APIView):
    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id, requiere_edicion=True):
            return _acceso_denegado()
        if not carga.archivo_temp_nombre:
            raise CarteraError('El archivo temporal ya no está disponible; vuelve a cargarlo.', codigo='ARCHIVO_NO_DISPONIBLE')

        mapeo = request.data.get('mapeo') or {}
        faltantes = column_mapper.campos_obligatorios_faltantes(mapeo)
        if faltantes:
            raise CarteraError(
                f'Faltan columnas obligatorias por mapear: {", ".join(faltantes)}.',
                codigo='MAPEO_INCOMPLETO',
                detalles={'campos_faltantes': faltantes},
            )

        hoja = request.data.get('hoja') or carga.nombre_hoja
        ruta_temp = settings.CARTERA_TEMP_UPLOADS_DIR / carga.archivo_temp_nombre
        df = excel_reader.leer_hoja(str(ruta_temp), hoja)

        errores_mapeo = column_mapper.validar_mapeo_contra_headers(mapeo, df.columns.tolist())
        if errores_mapeo:
            raise CarteraError('; '.join(errores_mapeo), codigo='MAPEO_INVALIDO')

        fecha_corte_raw = request.data.get('fecha_corte')
        fecha_corte = parse_fecha(fecha_corte_raw) if fecha_corte_raw else fecha_corte_por_defecto()

        registros, resumen = ingest.procesar_dataframe(df, mapeo, fecha_corte)

        RegistroCartera.objects.filter(carga_id=carga.id).delete()
        batch_size = settings.CARTERA_BULK_BATCH_SIZE
        objetos = [RegistroCartera(carga_id=carga.id, **r) for r in registros]
        RegistroCartera.objects.bulk_create(objetos, batch_size=batch_size)

        carga.estado = CargaArchivo.Estado.PROCESADO
        carga.fecha_corte = fecha_corte
        carga.mapeo_columnas = mapeo
        carga.resumen_validacion = resumen
        carga.filas_validas = resumen['filas_validas']
        carga.filas_advertencia = resumen['filas_con_advertencia']
        carga.filas_descartadas = resumen['filas_descartadas']

        try:
            os.remove(ruta_temp)
        except OSError:
            pass
        carga.archivo_temp_nombre = ''
        carga.save()

        df_valores = list(RegistroCartera.objects.filter(carga_id=carga.id).values(*CAMPOS_VALUES))
        df_kpis = pd.DataFrame(df_valores, columns=CAMPOS_VALUES) if df_valores else pd.DataFrame(columns=CAMPOS_VALUES)
        if not df_kpis.empty:
            df_kpis['saldo'] = df_kpis['saldo'].astype(float)
        kpis = resumen_kpis(df_kpis, fecha_corte)

        return Response({
            'carga_id': str(carga.id),
            **kpis,
            'resumen_validacion': {
                'filas_leidas': resumen['filas_leidas'],
                'filas_validas': resumen['filas_validas'],
                'filas_con_advertencia': resumen['filas_con_advertencia'],
                'filas_descartadas': resumen['filas_descartadas'],
                'advertencias_generales': resumen['advertencias_generales'],
            },
        }, status=200)


class ResumenView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        return Response(resumen_kpis(df, fecha_corte))


class TopClientesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        cartera_total = float(df.loc[df['saldo'] > 0, 'saldo'].sum()) if not df.empty else 0.0
        top_n = int(request.query_params.get('top_n', 10))
        return Response(aggregations.top_clientes(df, fecha_corte, cartera_total, top_n=top_n))


class ParetoCiudadesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        return Response(aggregations.pareto_ciudades(df, fecha_corte, agrupar_otras=True))


class RecuperadoresView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        return Response(aggregations.recuperadores(df, fecha_corte))


class CausalesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        df, _ = _df_anotado_y_filtrado(carga, request)
        return Response(aggregations.causales(df, agrupar_otras=True))


class RecuperadoresCausalesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        df, _ = _df_anotado_y_filtrado(carga, request)
        metrica = request.query_params.get('metrica', 'saldo')
        resultado = aggregations.recuperador_causal(df, metrica=metrica)
        formato = request.query_params.get('formato')
        if formato == 'matriz':
            return Response(resultado['matriz'])
        if formato == 'chart':
            return Response(resultado['chart'])
        return Response(resultado)


ORDENABLES = {
    'cliente', 'ruc_cliente', 'numero_documento', 'fecha_emision', 'fecha_vencimiento',
    'dias_vencidos', 'saldo', 'ciudad', 'recuperador', 'causal', 'estado_calculado', 'rango_mora',
}


def _buscar_y_ordenar(df, request):
    busqueda = request.query_params.get('buscar')
    if busqueda and not df.empty:
        patron = busqueda.strip()
        mascara = (
            df['cliente'].str.contains(patron, case=False, na=False)
            | df['ruc_cliente'].str.contains(patron, case=False, na=False)
            | df['numero_documento'].str.contains(patron, case=False, na=False)
        )
        df = df[mascara]

    orden = request.query_params.get('ordering')
    if orden:
        descendente = orden.startswith('-')
        campo = orden.lstrip('-')
        if campo in ORDENABLES and not df.empty:
            df = df.sort_values(campo, ascending=not descendente, na_position='last')

    return df


def _resolver_page(request):
    try:
        return max(int(request.query_params.get('page', 1)), 1)
    except (TypeError, ValueError):
        return 1


def _resolver_page_size(request):
    crudo = request.query_params.get('page_size')
    try:
        valor = int(crudo)
    except (TypeError, ValueError):
        return PAGE_SIZE_POR_DEFECTO
    if valor not in PAGE_SIZES_PERMITIDOS:
        logger.info('page_size no permitido recibido (%r); usando fallback %s', crudo, PAGE_SIZE_POR_DEFECTO)
        return PAGE_SIZE_POR_DEFECTO
    return valor


def _fila_a_dict(fila):
    return {
        'cliente': fila.get('cliente'),
        'ruc_cliente': fila.get('ruc_cliente'),
        'numero_documento': fila.get('numero_documento'),
        'fecha_emision': fila['fecha_emision'].isoformat() if pd.notna(fila.get('fecha_emision')) else None,
        'fecha_vencimiento': fila['fecha_vencimiento'].isoformat() if pd.notna(fila.get('fecha_vencimiento')) else None,
        'dias_vencidos': None if pd.isna(fila.get('dias_vencidos')) else int(fila['dias_vencidos']),
        'saldo': round(float(fila['saldo']), 2),
        'ciudad': fila.get('ciudad'),
        'recuperador': fila.get('recuperador'),
        'causal': fila.get('causal'),
        'estado_calculado': fila.get('estado_calculado'),
        'rango_mora': fila.get('rango_mora'),
    }


class DetalleView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        saldo_total_cartera = self._cartera_total_sin_filtrar(carga, request)

        df = _buscar_y_ordenar(df, request)

        page = _resolver_page(request)
        page_size = _resolver_page_size(request)
        total = len(df)
        inicio = (page - 1) * page_size
        pagina = df.iloc[inicio:inicio + page_size]

        saldo_filtrado = float(df['saldo'].sum()) if not df.empty else 0.0

        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'saldo_filtrado': round(saldo_filtrado, 2),
            'porcentaje_sobre_cartera_total': round((saldo_filtrado / saldo_total_cartera * 100) if saldo_total_cartera else 0.0, 2),
            'fecha_corte': fecha_corte.isoformat(),
            'results': [_fila_a_dict(f) for f in pagina.to_dict(orient='records')],
        })

    @staticmethod
    def _cartera_total_sin_filtrar(carga, request):
        fecha_corte = _resolver_fecha_corte(request, carga)
        valores = list(RegistroCartera.objects.filter(carga_id=carga.id).values(*CAMPOS_VALUES))
        if not valores:
            return 0.0
        df = pd.DataFrame(valores)
        df['saldo'] = df['saldo'].astype(float)
        return float(df.loc[df['saldo'] > 0, 'saldo'].sum())


class ExportarView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        formato = request.query_params.get('formato', 'xlsx')
        tipo = request.query_params.get('tipo', 'detalle')

        if tipo == 'errores':
            resumen = carga.resumen_validacion or {}
            filas = resumen.get('descartados', [])
            columnas = export_service.COLUMNAS_ERRORES
            nombre_base = 'errores_cartera'
        else:
            df, _ = _df_anotado_y_filtrado(carga, request)
            df = _buscar_y_ordenar(df, request)
            filas = [_fila_a_dict(f) for f in df.to_dict(orient='records')]
            columnas = export_service.COLUMNAS_DETALLE
            nombre_base = 'detalle_cartera'

        if formato == 'csv':
            buffer = export_service.generar_csv(filas, columnas)
            respuesta = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
            respuesta['Content-Disposition'] = f'attachment; filename="{nombre_base}.csv"'
        else:
            buffer = export_service.generar_excel(filas, columnas)
            respuesta = HttpResponse(
                buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            respuesta['Content-Disposition'] = f'attachment; filename="{nombre_base}.xlsx"'

        return respuesta


class ArchivoView(APIView):
    def delete(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id, requiere_edicion=True):
            return _acceso_denegado()
        if carga.archivo_temp_nombre:
            ruta_temp = settings.CARTERA_TEMP_UPLOADS_DIR / carga.archivo_temp_nombre
            try:
                os.remove(ruta_temp)
            except OSError:
                pass
        # Borra en cascada sus `FilaArchivoHistorico` (FK `on_delete=CASCADE`, sección 28): si
        # esta carga alimentaba una tabla histórica, esas filas dejan de existir con ella.
        carga.delete()
        return Response(status=204)


class HistoricoCargasView(APIView):
    """`GET /api/cartera/historico/cargas?dashboard_id=...` — las cargas de un dashboard que ya
    tienen filas históricas guardadas (sección 28: se guardan al aplicar el mapeo de la
    plantilla), de más antigua a más nueva, junto con las columnas disponibles para armar una tabla
    histórica (`columnas_disponibles`) y las columnas marcadas como históricas para este dashboard
    (`columnas_historicas_configuradas`) — ambas son, a propósito, la misma configuración
    persistente (`ColumnaHistorica`), no lo observado en los datos guardados: se usa para pre-tildar
    el paso "Renombrar columnas", para que Tabla 3 sepa qué comparar, y para limitar el
    selector de "Histórico de cargas" a solo lo que el usuario marcó a propósito."""

    def get(self, request):
        dashboard_id = request.query_params.get('dashboard_id')
        if not dashboard_id:
            raise CarteraError('dashboard_id es requerido.', codigo='DASHBOARD_ID_REQUERIDO')
        if not _tiene_acceso(request, dashboard_id):
            return _acceso_denegado()
        resultado = historico.listar_cargas_historicas(dashboard_id)
        resultado['columnas_historicas_configuradas'] = historico.columnas_historicas_configuradas(dashboard_id)
        return Response(resultado)


class HistoricoTablaView(APIView):
    """`POST /api/cartera/historico/tabla` — una fila por carga histórica *habilitada* del
    dashboard (o solo las de `carga_ids`, si se pasa — bypasea el filtro de habilitadas), con el
    valor de cada columna de `columnas_valor` agregado según el tipo de cálculo elegido para esa
    columna (suma/promedio/conteo de valores únicos). Misma forma `{columnas, filas}` que ya
    renderiza `GenericDataTable` en el frontend."""

    def post(self, request):
        dashboard_id = request.data.get('dashboard_id')
        if not dashboard_id:
            raise CarteraError('dashboard_id es requerido.', codigo='DASHBOARD_ID_REQUERIDO')
        if not _tiene_acceso(request, dashboard_id):
            return _acceso_denegado()
        columnas_valor = request.data.get('columnas_valor') or []
        carga_ids = request.data.get('carga_ids') or None
        return Response(historico.calcular_tabla_historica(dashboard_id, columnas_valor, carga_ids))


class HistoricoArchivoView(APIView):
    """`GET /api/cartera/historico/cargas/<carga_id>/archivo` — todas las columnas y filas
    guardadas de UNA carga histórica puntual (sección 29), para poder ver el archivo completo
    ("Ver archivo" en la pantalla de histórico) sin descargarlo."""

    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id):
            return _acceso_denegado()
        return Response(historico.obtener_filas_archivo(carga))


class HistoricoCargaIncluidaView(APIView):
    """`PATCH /api/cartera/historico/cargas/<carga_id>/incluir` — habilita/deshabilita una carga
    puntual para la comparación histórica del dashboard (checkbox en "Histórico de cargas", persiste
    de inmediato — mismo criterio que la Zona Personal del editor visual). Afecta tanto la vista
    previa que arma esa pantalla como Tabla 3 dentro del dashboard real, ya que ambas usan
    `historico.calcular_tabla_historica` sin `carga_ids`."""

    def patch(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        if not _tiene_acceso(request, carga.dashboard_id, requiere_edicion=True):
            return _acceso_denegado()
        if 'incluir' not in request.data:
            raise CarteraError('incluir es requerido.', codigo='INCLUIR_REQUERIDO')
        carga = historico.establecer_carga_incluida_en_historico(carga, request.data.get('incluir'))
        return Response({'carga_id': str(carga.id), 'incluir_en_historico': carga.incluir_en_historico})
