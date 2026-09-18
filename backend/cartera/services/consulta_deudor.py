"""Consulta puntual de un deudor: su antigüedad de cartera y sus documentos.

Responde una pregunta que las secciones del Directorio no contestan: las de concentración y
mayores deudores muestran a los más grandes, pero nadie puede preguntar por UN cliente en
particular ("¿cómo está la cartera de Transexpress?"). Acá se busca por nombre o identificador y
se devuelve su antigüedad por tramos más las filas del archivo donde aparece.

Lee el archivo de la carga vigente en vez de una tabla: los dashboards genéricos —el Directorio
entre ellos— no insertan sus filas en `RegistroCartera` (eso es del dashboard legado de cartera),
así que el Excel guardado es la única fuente. Son ~2.700 filas por archivo, una lectura de
milisegundos; si algún día un archivo creciera lo suficiente como para que eso pese, el lugar de
la caché es acá y no en el llamador.

La antigüedad se calcula con `generic_charts.generar_datos_tramos_antiguedad`, la MISMA función que
alimenta el gráfico del dashboard: si se calculara aparte, el total de un cliente podría no cuadrar
con el tramo al que el gráfico lo asigna. Esa función ya devuelve los seis tramos siempre, con 0 en
los que no tienen filas.
"""

import datetime
import unicodedata

import pandas as pd

from . import carga_archivos, generic_charts
from ..exceptions import CarteraError
from ..models import CargaArchivo

# Cuántas coincidencias devuelve la búsqueda. El buscador es para elegir un cliente, no para
# navegar el padrón entero: con más de esto, lo que hace falta es afinar el texto.
LIMITE_COINCIDENCIAS = 25


def _texto(serie):
    """Serie de texto sin vacíos, sin el `fillna('')` que pandas 2.2 marca como obsoleto sobre
    columnas de tipo objeto (avisa que va a cambiar el tipo resultante en una versión futura)."""
    return serie.where(serie.notna(), '').astype(str)


def _normalizar(texto):
    """Sin acentos, sin espacios de sobra y en minúsculas — para que "PEÑA" encuentre "peña" y
    "Peña" encuentre "PENA", que es como se escriben los nombres en la práctica."""
    crudo = str(texto or '').strip().lower()
    return ''.join(c for c in unicodedata.normalize('NFD', crudo)
                   if unicodedata.category(c) != 'Mn')


def _carga_vigente(dashboard_id):
    carga = (
        CargaArchivo.objects
        .filter(dashboard_id=dashboard_id, estado=CargaArchivo.Estado.PROCESADO)
        .order_by('-fecha_carga')
        .first()
    )
    if not carga:
        raise CarteraError(
            'Este dashboard todavía no tiene un archivo cargado para consultar.',
            codigo='SIN_CARGA_PARA_CONSULTAR',
        )
    return carga


def _df_de(dashboard_id):
    carga = _carga_vigente(dashboard_id)
    _, df = carga_archivos.leer_archivo_de_carga(carga)
    return df, carga


def _validar_columnas(df, columnas):
    faltantes = [c for c in columnas if c and c not in df.columns]
    if faltantes:
        raise CarteraError(
            'El archivo cargado ya no tiene estas columnas: ' + ', '.join(faltantes) + '.',
            codigo='COLUMNAS_NO_DISPONIBLES',
            detalles={'columnas': faltantes},
        )


def _identidad(df, columna_nombre, columna_ruc):
    """Clave de agrupación: el identificador si lo hay, el nombre si no.

    Misma regla que el resto del proyecto (identificador → nombre): dos filas del mismo RUC son el
    mismo cliente aunque el nombre venga escrito distinto, que pasa seguido con sufijos como
    "S.A." o "CIA. LTDA.".
    """
    nombres = _texto(df[columna_nombre]).str.strip()
    if not columna_ruc or columna_ruc not in df.columns:
        return nombres.replace('', 'Sin dato')
    rucs = _texto(df[columna_ruc]).str.strip()
    return rucs.where(rucs != '', nombres).replace('', 'Sin dato')


def columnas_disponibles(dashboard_id):
    """Las columnas del archivo vigente, para que el panel de configuración ofrezca cuáles mostrar.

    Se resuelve acá y no en el frontend porque las columnas son del ARCHIVO, no del layout: cambian
    cuando se carga uno nuevo, y una lista guardada en la configuración envejecería sin aviso.
    """
    df, carga = _df_de(dashboard_id)
    return {
        'columnas': [str(c) for c in df.columns],
        'archivo': carga.nombre_original,
        'fecha_corte': carga.fecha_corte.isoformat() if carga.fecha_corte else None,
    }


def buscar(dashboard_id, texto, columna_nombre, columna_valor, columna_ruc=None):
    """Clientes cuyo nombre o identificador contiene `texto`, con su saldo y cuántas filas tienen.

    Devuelve coincidencias para que la interfaz deje ELEGIR una, en vez de sumar a ciegas todo lo
    que coincida: "transex" puede tocar a dos razones sociales distintas, y sumarlas daría un total
    que no le corresponde a ninguna.
    """
    texto_normalizado = _normalizar(texto)
    if len(texto_normalizado) < 2:
        raise CarteraError('Escribí al menos dos caracteres para buscar.', codigo='BUSQUEDA_MUY_CORTA')

    df, _ = _df_de(dashboard_id)
    _validar_columnas(df, [columna_nombre, columna_valor])

    nombres = _texto(df[columna_nombre])
    rucs = _texto(df[columna_ruc]) if columna_ruc and columna_ruc in df.columns else None

    coincide = nombres.map(lambda v: texto_normalizado in _normalizar(v))
    if rucs is not None:
        coincide = coincide | rucs.map(lambda v: texto_normalizado in _normalizar(v))

    encontrados = df[coincide]
    if encontrados.empty:
        return {'coincidencias': [], 'total': 0}

    identidad = _identidad(encontrados, columna_nombre, columna_ruc)
    valores = pd.to_numeric(encontrados[columna_valor], errors='coerce').fillna(0)

    agrupado = (
        pd.DataFrame({
            'identidad': identidad,
            'nombre': _texto(encontrados[columna_nombre]),
            'valor': valores,
        })
        .groupby('identidad', as_index=False)
        .agg(nombre=('nombre', 'first'), saldo=('valor', 'sum'), filas=('valor', 'size'))
        .sort_values('saldo', ascending=False)
    )

    coincidencias = [
        {
            'identidad': str(fila.identidad),
            'nombre': str(fila.nombre),
            'saldo': round(float(fila.saldo), 2),
            'filas': int(fila.filas),
        }
        for fila in agrupado.head(LIMITE_COINCIDENCIAS).itertuples()
    ]
    return {'coincidencias': coincidencias, 'total': int(len(agrupado))}


def detalle(dashboard_id, identidad, columna_nombre, columna_fecha, columna_valor,
            columna_ruc=None, columnas_detalle=None):
    """Antigüedad por tramos y filas del archivo para un cliente puntual.

    `columnas_detalle` acota qué columnas devuelve el detalle; sin eso viajarían las 28 del archivo
    en cada consulta. Las que no existan en el archivo se ignoran en vez de fallar: el mapeo de
    columnas se puede haber guardado con un archivo anterior.
    """
    df, carga = _df_de(dashboard_id)
    _validar_columnas(df, [columna_nombre, columna_fecha, columna_valor])

    identidades = _identidad(df, columna_nombre, columna_ruc)
    del_deudor = df[identidades.astype(str) == str(identidad)]
    if del_deudor.empty:
        raise CarteraError(
            'No se encontraron filas para ese cliente en el archivo vigente.',
            codigo='DEUDOR_SIN_FILAS',
        )

    tramos = generic_charts.generar_datos_tramos_antiguedad(
        del_deudor, columna_fecha, columna_valor, fecha_referencia=carga.fecha_corte,
    )

    valores = pd.to_numeric(del_deudor[columna_valor], errors='coerce').fillna(0)
    total = float(valores.sum())

    disponibles = [str(c) for c in df.columns]
    elegidas = [c for c in (columnas_detalle or disponibles) if c in df.columns]
    if not elegidas:
        elegidas = disponibles

    # `where(notna)` deja los vacíos como None: sin eso viajan como el texto "nan" y la tabla los
    # muestra tal cual.
    filas = del_deudor[elegidas].astype(object).where(pd.notna(del_deudor[elegidas]), None)

    return {
        'identidad': str(identidad),
        'nombre': str(_texto(del_deudor[columna_nombre]).iloc[0]),
        'total': round(total, 2),
        'cantidad_filas': int(len(del_deudor)),
        'fecha_corte': carga.fecha_corte.isoformat() if carga.fecha_corte else None,
        'tramos': {
            'categorias': tramos['categorias'] if tramos else [],
            'valores': tramos['valores'] if tramos else [],
        },
        'columnas_disponibles': disponibles,
        'columnas': elegidas,
        'filas': [
            [_valor_serializable(v) for v in fila]
            for fila in filas.itertuples(index=False, name=None)
        ],
    }


def _valor_serializable(valor):
    """Fechas a ISO y numpy a tipos nativos — el resto, tal cual. Lo que va por JSON tiene que ser
    JSON, y del Excel salen `Timestamp`, `datetime` y `int64`, que el serializador no convierte.

    `datetime` se comprueba además de `Timestamp` porque el lector devuelve uno u otro según cómo
    venga la columna en el archivo; con solo `Timestamp`, las fechas de algunas columnas llegaban
    al frontend como el `repr` de Python.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, (pd.Timestamp, datetime.datetime, datetime.date)):
        return valor.date().isoformat() if hasattr(valor, 'date') else valor.isoformat()
    if hasattr(valor, 'item'):  # numpy
        return valor.item()
    return valor
