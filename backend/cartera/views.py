import os
import uuid

import pandas as pd
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from .exceptions import CarteraError
from .models import CargaArchivo, RegistroCartera
from .services import aggregations, column_mapper, export_service, excel_reader, filters, ingest
from .services.calculator import anotar_estado_y_mora, resumen_kpis
from .utils.dates import fecha_corte_por_defecto, parse_fecha

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
            nombre_original=nombre_original,
            nombre_hoja=hoja,
            tamano_bytes=archivo.size,
            estado=CargaArchivo.Estado.VALIDADO,
            total_filas_excel=len(df),
            archivo_temp_nombre=nombre_temp,
        )

        return Response({
            'carga_id': str(carga.id),
            'nombre_archivo': nombre_original,
            'tamano_bytes': archivo.size,
            'fecha_carga': carga.fecha_carga.isoformat(),
            'hojas_disponibles': hojas,
            'hoja_seleccionada': hoja,
            'total_filas_detectadas': len(df),
            'mapeo_sugerido': mapeo_sugerido,
            'preview': preview,
        }, status=200)


class ProcesarView(APIView):
    def post(self, request):
        carga_id = request.data.get('carga_id')
        if not carga_id:
            raise CarteraError('carga_id es requerido.', codigo='CARGA_ID_REQUERIDO')

        carga = get_object_or_404(CargaArchivo, id=carga_id)
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
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        return Response(resumen_kpis(df, fecha_corte))


class TopClientesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        cartera_total = float(df.loc[df['saldo'] > 0, 'saldo'].sum()) if not df.empty else 0.0
        top_n = int(request.query_params.get('top_n', 10))
        return Response(aggregations.top_clientes(df, fecha_corte, cartera_total, top_n=top_n))


class ParetoCiudadesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        return Response(aggregations.pareto_ciudades(df, fecha_corte, agrupar_otras=True))


class RecuperadoresView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        return Response(aggregations.recuperadores(df, fecha_corte))


class CausalesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
        df, _ = _df_anotado_y_filtrado(carga, request)
        return Response(aggregations.causales(df, agrupar_otras=True))


class RecuperadoresCausalesView(APIView):
    def get(self, request, carga_id):
        carga = get_object_or_404(CargaArchivo, id=carga_id)
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
        df, fecha_corte = _df_anotado_y_filtrado(carga, request)
        saldo_total_cartera = self._cartera_total_sin_filtrar(carga, request)

        df = _buscar_y_ordenar(df, request)

        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = min(max(int(request.query_params.get('page_size', 50)), 1), 1000)
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
        if carga.archivo_temp_nombre:
            ruta_temp = settings.CARTERA_TEMP_UPLOADS_DIR / carga.archivo_temp_nombre
            try:
                os.remove(ruta_temp)
            except OSError:
                pass
        carga.delete()
        return Response(status=204)
