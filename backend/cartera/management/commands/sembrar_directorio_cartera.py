"""`python manage.py sembrar_directorio_cartera --archivo "ruta.xlsx"`

Construye el "Dashboard Directorio" (4 KPI + gráfico de antigüedad + tabla de cumplimiento de metas
+ tabla de concentración) con datos reales de un archivo.

Existe como comando y no como parte del flujo normal de carga porque este dashboard es la excepción
declarada del proyecto: no usa las 13 posiciones de la plantilla genérica, así que el asistente de
"Cargar archivo → mapear columnas" no puede producirlo.

**Simula por defecto**: sin `--aplicar` informa qué calcularía sin escribir nada, igual que
`reprocesar_dashboards`.
"""

import uuid

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from cartera.models import CargaArchivo
from cartera.services import directorio_cartera
from cartera.services.carga_archivos import HOJA_ARCHIVO_PERMANENTE
from cartera.utils.archivos import asegurar_directorio
from cartera.utils.dates import fecha_corte_por_defecto

DASHBOARD_POR_DEFECTO = 'directorio-cartera'
# El archivo de origen trae una fila de título sobre los encabezados reales, así que estos están en
# la segunda fila. Es configurable porque el próximo archivo podría no traerla.
FILA_ENCABEZADO_POR_DEFECTO = 2


class Command(BaseCommand):
    help = 'Construye el Dashboard Directorio con datos reales de un archivo Excel.'

    def add_arguments(self, parser):
        parser.add_argument('--archivo', required=True, help='Ruta del .xlsx de origen.')
        parser.add_argument('--dashboard', default=DASHBOARD_POR_DEFECTO)
        parser.add_argument('--hoja', default=None, help='Hoja a leer (por defecto, la primera).')
        parser.add_argument(
            '--fila-encabezado', type=int, default=FILA_ENCABEZADO_POR_DEFECTO,
            help=f'Fila (1-based) con los encabezados. Por defecto {FILA_ENCABEZADO_POR_DEFECTO}.',
        )
        parser.add_argument('--fecha-corte', default=None, help='ISO (YYYY-MM-DD). Por defecto, el último día del mes anterior.')
        # Las columnas y el Top-N son PARÁMETROS, no constantes: quedan guardados en el `mapeo` de
        # cada sección y después se editan desde "Configurar componente → Datos" sin tocar código.
        parser.add_argument('--columna-valor', default=directorio_cartera.COLUMNA_VALOR)
        parser.add_argument('--columna-fecha', default=directorio_cartera.COLUMNA_FECHA)
        parser.add_argument('--columna-cliente', default=directorio_cartera.COLUMNA_CLIENTE)
        parser.add_argument('--top-n', type=int, default=directorio_cartera.TOP_N)
        parser.add_argument('--aplicar', action='store_true', help='Escribe los cambios.')

    def handle(self, *args, **opciones):
        df = self._leer(opciones)
        fecha_corte = self._fecha_corte(opciones)
        dashboard_id = opciones['dashboard']

        columnas = {
            'columna_valor': opciones['columna_valor'], 'columna_fecha': opciones['columna_fecha'],
            'columna_cliente': opciones['columna_cliente'],
        }
        faltantes = directorio_cartera.columnas_faltantes(df, **columnas)
        if faltantes:
            raise CommandError(
                f'Al archivo le faltan columnas que este dashboard necesita: {", ".join(faltantes)}. '
                f'Encontradas: {", ".join(map(str, df.columns[:12]))}…'
            )

        self.stdout.write(f'Archivo: {len(df)} fila(s), {len(df.columns)} columna(s). Fecha de corte: {fecha_corte}.')

        parametros = {**columnas, 'top_n': opciones['top_n']}

        if not opciones['aplicar']:
            self._simular(df, fecha_corte, parametros)
            return

        resultados = directorio_cartera.construir(dashboard_id, df, fecha_corte, **parametros)
        self._registrar_carga(dashboard_id, df, fecha_corte)

        for component_id, calculado in resultados:
            estilo = self.style.SUCCESS if calculado else self.style.WARNING
            self.stdout.write(estilo(f'  {component_id}: {"calculado" if calculado else "SIN DATOS"}'))
        self.stdout.write(self.style.SUCCESS(f'Listo. {dashboard_id} reconstruido con datos reales.'))

    def _leer(self, opciones):
        ruta = opciones['archivo']
        try:
            libro = pd.ExcelFile(ruta)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo de apertura es un archivo inválido
            raise CommandError(f'No se pudo abrir "{ruta}": {exc}')
        hoja = opciones['hoja'] or libro.sheet_names[0]
        df = pd.read_excel(ruta, sheet_name=hoja, header=opciones['fila_encabezado'] - 1)
        # Los encabezados de un Excel real llegan con espacios de sobra; el mapeo los compara literal.
        df.columns = [str(columna).strip() for columna in df.columns]
        return df

    def _fecha_corte(self, opciones):
        if not opciones['fecha_corte']:
            return fecha_corte_por_defecto()
        from datetime import date
        try:
            return date.fromisoformat(opciones['fecha_corte'])
        except ValueError:
            raise CommandError(f'La fecha de corte "{opciones["fecha_corte"]}" no es una fecha ISO válida.')

    def _simular(self, df, fecha_corte, parametros):
        self.stdout.write(self.style.MIGRATE_HEADING('SIMULACIÓN (no se escribe nada)'))
        for spec, contenido in directorio_cartera.calcular_contenidos(df, fecha_corte, **parametros):
            self.stdout.write(f'  {spec["component_id"]}: {self._resumen(contenido)}')
        self.stdout.write('')
        self.stdout.write('Volvé a ejecutarlo con --aplicar para escribir los cambios.')

    @staticmethod
    def _resumen(contenido):
        if contenido is None:
            return 'SIN DATOS (revisá las columnas elegidas)'
        if 'valor' in contenido:
            return f'{contenido["valor"]:,.2f}'
        if 'categorias' in contenido:
            return ' · '.join(f'{c}={v:,.0f}' for c, v in zip(contenido['categorias'], contenido['valores']))
        if 'filas' in contenido:
            return f'{len(contenido["filas"])} fila(s)'
        return 'contenido calculado'

    def _registrar_carga(self, dashboard_id, df, fecha_corte):
        """Deja una `CargaArchivo` procesada con una copia normalizada del archivo.

        Sin esto el dashboard quedaría con datos pero sin rastro de su origen: no aparecería en
        "Histórico de cargas" ni habría de dónde releerlo para recalcular más adelante.
        """
        carga = CargaArchivo.objects.create(
            id=uuid.uuid4(), dashboard_id=dashboard_id,
            nombre_original='Dashboard Directorio (carga inicial).xlsx',
            estado=CargaArchivo.Estado.PROCESADO, fecha_corte=fecha_corte,
            total_filas_excel=len(df), filas_validas=len(df),
        )
        nombre = f'{carga.id}.xlsx'
        ruta = asegurar_directorio(settings.CARTERA_ARCHIVOS_DIR) / nombre
        # Se guarda YA normalizado (encabezados en la primera fila): quien lo relea después no tiene
        # que volver a adivinar dónde empezaban.
        df.to_excel(ruta, index=False, sheet_name=HOJA_ARCHIVO_PERMANENTE)
        carga.archivo_permanente_nombre = nombre
        carga.save(update_fields=['archivo_permanente_nombre'])
        self.stdout.write(f'  carga registrada: {carga.id}')
