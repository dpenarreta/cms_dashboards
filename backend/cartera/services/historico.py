"""Histórico de archivos cargados (sección 28): persiste, de cada archivo aplicado a la plantilla
(`AplicarMapeoPlantillaView`), únicamente las columnas que el usuario marcó como "históricas" en el
paso "Renombrar columnas" (`ColumnaHistorica`, configuración persistente por dashboard — se
reconocen solas en la próxima carga) — para poder armar tablas históricas comparando varias cargas
del mismo dashboard a través del tiempo, sin depender de que el archivo físico original siga
existiendo en disco. A diferencia del dominio clásico de cartera (`RegistroCartera`, esquema fijo),
este módulo no asume ninguna columna en particular: trabaja sobre el mismo `DataFrame` genérico que
ya usa `services/plantilla.py`. Además de qué COLUMNAS comparar (`ColumnaHistorica`), cada carga
puede habilitarse/deshabilitarse individualmente para el cálculo (`CargaArchivo.incluir_en_historico`,
`establecer_carga_incluida_en_historico`) — ambos flags son independientes: uno decide qué columnas
se persisten y comparan, el otro qué cargas cuentan.
"""

import pandas as pd
from django.conf import settings

from ..models import CargaArchivo, ColumnaHistorica, FilaArchivoHistorico
from . import generic_charts


def guardar_filas_historicas(carga, df, columnas_historicas):
    """Reemplaza las filas históricas de `carga` por las de `df`, pero **solo para las columnas en
    `columnas_historicas`** (nombres ya renombrados por alias, ver `ColumnaHistorica`) — de acá en
    adelante ya no se persiste la fila completa, sino únicamente lo que el usuario marcó como
    histórico en el paso "Renombrar columnas". Una columna marcada que ya no existe en `df` se
    ignora sin romper; si no queda ninguna columna válida, no se crea ninguna fila (pero sí se
    borran las anteriores de esta carga — mismo criterio idempotente que
    `services/ingest.py::procesar_dataframe` para `RegistroCartera`: reaplicar el mismo mapeo sobre
    la misma carga no duplica ni deja basura vieja). Convierte cada celda a JSON-seguro con el
    mismo criterio ya usado en `services/ingest.py::_valor_crudo` (NaN/NaT/None → `None`) —
    `DataFrame.where(...)` no sirve para esto: en una columna float, pandas puede dejar el NaN sin
    reemplazar en vez de escribir `None`, lo que después rompe la restricción CHECK de JSON válido
    en SQL Server."""
    FilaArchivoHistorico.objects.filter(carga=carga).delete()

    columnas_presentes = [c for c in columnas_historicas if c in df.columns]
    if not columnas_presentes:
        return

    registros = df[columnas_presentes].to_dict(orient='records')
    objetos = [
        FilaArchivoHistorico(
            carga=carga, orden=indice,
            datos={columna: (None if pd.isna(valor) else valor) for columna, valor in fila.items()},
        )
        for indice, fila in enumerate(registros)
    ]
    FilaArchivoHistorico.objects.bulk_create(objetos, batch_size=settings.CARTERA_BULK_BATCH_SIZE)


def columnas_historicas_configuradas(dashboard_id):
    """Las columnas que el usuario ya marcó como históricas para este dashboard en una carga
    anterior (`ColumnaHistorica`) — se usa para reconocerlas solas (pre-tildadas) en la próxima
    carga, y para que Tabla 3 sepa qué comparar sin que el usuario tenga que elegir nada
    en el paso de Mapeo."""
    return list(ColumnaHistorica.objects.filter(dashboard_id=dashboard_id).values_list('columna', flat=True))


def establecer_columnas_historicas(dashboard_id, columnas):
    """Reemplaza por completo la configuración de columnas históricas de este dashboard — lo que
    se manda ahora ES la nueva configuración (no se acumula), así desmarcar una columna la saca de
    verdad. Se llama junto con `guardar_filas_historicas` al aplicar el mapeo
    (`AplicarMapeoPlantillaView`)."""
    ColumnaHistorica.objects.filter(dashboard_id=dashboard_id).delete()
    nombres = list(dict.fromkeys(str(c).strip() for c in (columnas or []) if str(c or '').strip()))
    ColumnaHistorica.objects.bulk_create([
        ColumnaHistorica(dashboard_id=dashboard_id, columna=nombre) for nombre in nombres
    ])


def listar_cargas_historicas(dashboard_id):
    """Las cargas de `dashboard_id` que sí tienen filas históricas (las que llegaron a aplicarse a
    la plantilla), de más antigua a más nueva, junto con las columnas disponibles para comparar.
    `columnas_disponibles` son las columnas marcadas como históricas para este dashboard
    (`columnas_historicas_configuradas`) — no lo que efectivamente haya guardado cada carga: las
    cargas de antes de esta configuración persisten la fila completa (ver `guardar_filas_historicas`)
    y esas columnas extra no le sirven al usuario para comparar, solo las que marcó a propósito.
    Incluye `incluir_en_historico` por carga (ver `CargaArchivo.incluir_en_historico`) para que el
    frontend refleje el estado real del checkbox de "Histórico de cargas", tanto las habilitadas
    como las deshabilitadas — a diferencia de `calcular_tabla_historica`, que sin `carga_ids`
    excluye directamente las deshabilitadas."""
    cargas = list(
        CargaArchivo.objects.filter(dashboard_id=dashboard_id, filas_historicas__isnull=False)
        .distinct().order_by('fecha_carga'),
    )

    return {
        'cargas': [
            {
                'carga_id': str(carga.id),
                'nombre_original': carga.nombre_original,
                'fecha_carga': carga.fecha_carga.isoformat(),
                'fecha_corte': carga.fecha_corte.isoformat() if carga.fecha_corte else None,
                'total_filas': FilaArchivoHistorico.objects.filter(carga=carga).count(),
                'incluir_en_historico': carga.incluir_en_historico,
            }
            for carga in cargas
        ],
        'columnas_disponibles': columnas_historicas_configuradas(dashboard_id),
    }


def establecer_carga_incluida_en_historico(carga, incluida):
    """Marca/desmarca una carga puntual para que cuente (o no) en `calcular_tabla_historica` de su
    dashboard — Tabla 3 dentro del dashboard y "Histórico de cargas" respetan este mismo flag, así
    que desmarcar una carga acá la excluye de ambos lugares por igual. No borra
    `FilaArchivoHistorico`: los datos siguen guardados, solo se excluyen del cálculo mientras esté
    deshabilitada, así se puede volver a habilitar sin perder nada."""
    carga.incluir_en_historico = bool(incluida)
    carga.save(update_fields=['incluir_en_historico'])
    return carga


def obtener_filas_archivo(carga):
    """Todas las columnas y filas guardadas de UNA carga puntual, tal como se persistieron al
    aplicar el mapeo (sección 29) — a diferencia de `calcular_tabla_historica`, sin agregar nada:
    cada fila del archivo original tal cual, para poder ver el archivo completo (todas las
    columnas, todas las filas) sin necesitar el archivo físico ni descargarlo. Misma forma
    `{columnas, filas}` que ya entiende `GenericDataTable` en el frontend."""
    filas_historicas = list(FilaArchivoHistorico.objects.filter(carga=carga).order_by('orden'))
    if not filas_historicas:
        return {'columnas': [], 'filas': []}

    columnas = list(filas_historicas[0].datos.keys())
    filas = [[fila.datos.get(columna) for columna in columnas] for fila in filas_historicas]
    return {'columnas': columnas, 'filas': filas}


def calcular_tabla_historica(dashboard_id, columnas_valor, carga_ids=None):
    """Una fila por carga (ordenadas de más antigua a más nueva), con el valor de cada columna
    pedida agregado con el tipo de cálculo elegido para ESA columna (suma/promedio/conteo de
    valores únicos/valor de celda — mismo criterio y misma función, `generic_charts.valor_agregado`,
    que ya usa `generar_datos_tabla` dentro de un solo archivo, ahora aplicada a través de varias
    cargas). Devuelve directamente la forma `{columnas, filas}` que ya entiende `GenericDataTable`
    en el frontend (identidad = archivo/usuario que lo subió/fecha de carga/fecha de corte, luego
    una columna por cada entrada de `columnas_valor`) — "Archivo" va primero porque siempre tiene un
    valor (a diferencia de "Fecha de corte", opcional): es la columna que el frontend usa como
    identidad de la fila para el párrafo de "Hallazgos clave" ("X tiene el mayor valor de..."),
    así que no puede quedar vacía. Sin fila de `total`: sumar un "promedio por carga" entre cargas
    sería engañoso.

    Sin `carga_ids`, solo entran las cargas con `incluir_en_historico=True` — es el caso de Tabla 3
    dentro del dashboard (`TablaHistoricaAutomatica.jsx`, nunca manda `carga_ids`) y de "Generar
    tabla histórica" en "Histórico de cargas", que ya no arma esa lista a mano: el checkbox por
    carga de esa pantalla persiste el mismo flag (`establecer_carga_incluida_en_historico`) en vez
    de armar una selección efímera. Pasar `carga_ids` explícito sigue siendo una selección puntual
    que puede incluir una carga deshabilitada — la usan los tests y queda disponible para casos
    futuros que necesiten esa precisión."""
    entradas = [generic_charts.normalizar_columna_valor_tabla(c) for c in (columnas_valor or [])]
    nombres_columna = [e['columna'] for e in entradas if e['columna']]

    cargas_qs = (
        CargaArchivo.objects.filter(dashboard_id=dashboard_id, filas_historicas__isnull=False)
        .distinct().select_related('subido_por')
    )
    if carga_ids:
        cargas_qs = cargas_qs.filter(id__in=carga_ids)
    else:
        cargas_qs = cargas_qs.filter(incluir_en_historico=True)
    cargas = list(cargas_qs.order_by('fecha_carga'))

    columnas = ['Archivo', 'Usuario', 'Fecha de carga', 'Fecha de corte'] + nombres_columna
    filas = []
    for carga in cargas:
        valores_por_fila = FilaArchivoHistorico.objects.filter(carga=carga).order_by('orden').values_list('datos', flat=True)
        fila = [
            carga.nombre_original,
            carga.subido_por.username if carga.subido_por else 'Desconocido',
            carga.fecha_carga.date().isoformat(),
            carga.fecha_corte.isoformat() if carga.fecha_corte else '',
        ]
        for entrada in entradas:
            if not entrada['columna']:
                fila.append(None)
                continue
            serie = pd.Series([datos.get(entrada['columna']) for datos in valores_por_fila])
            valor = generic_charts.valor_agregado(serie, entrada['tipo_agregacion'])
            if not pd.notna(valor):
                fila.append(None)
            elif entrada['tipo_agregacion'] == 'valor_celda':
                fila.append(valor)
            else:
                fila.append(round(float(valor), 2))
        filas.append(fila)

    return {'columnas': columnas, 'filas': filas}
