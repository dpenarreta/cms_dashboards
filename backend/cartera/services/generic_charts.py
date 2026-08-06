"""Análisis genérico de columnas de un archivo cargado, recomendación de gráficas a partir de ese
análisis, y cálculo de los datos de cada gráfica confirmada — a diferencia del resto del paquete
`services/` (column_mapper, ingest, calculator, aggregations), este módulo no asume ningún esquema
de negocio fijo (cliente/saldo/causal/...): se aplica a cualquier archivo subido a cualquier
dashboard. Flujo: cargar archivo → analizar columnas (con alias editables en el frontend) →
recomendar gráficas → el usuario agrega, una por una, las que le sirven."""

import pandas as pd

CARDINALIDAD_MAXIMA_CATEGORIA = 50
LIMITE_CATEGORIAS_EN_GRAFICA = 15
# Tope de seguridad de `generar_datos_tabla` (no una cantidad "a mostrar": el frontend pagina
# sobre lo que llegue, con su propio selector de 5/10/20/25/50 filas por página, sección 24) —
# protege el tamaño de la respuesta cuando la columna de identidad elegida tiene una cardinalidad
# alta, sin impedir "ver toda la tabla" en el caso normal de una identidad de baja/media
# cardinalidad (producto, región, vendedor...).
LIMITE_FILAS_TABLA = 500
# Datos reales de negocio traen valores sueltos inválidos ("no aplica", celdas mal tipeadas) — un
# 80% de valores convertibles alcanza para clasificar la columna como numérica/fecha sin exigir
# que el archivo esté perfectamente limpio.
UMBRAL_RATIO_TIPO = 0.8


def _ratio_convertible(serie_sin_nulos, convertir):
    if len(serie_sin_nulos) == 0:
        return 0.0
    convertida = convertir(serie_sin_nulos)
    return float(convertida.notna().mean())


def _detectar_tipo(serie_sin_nulos):
    if _ratio_convertible(serie_sin_nulos, lambda s: pd.to_numeric(s, errors='coerce')) >= UMBRAL_RATIO_TIPO:
        return 'numerico'
    if _ratio_convertible(serie_sin_nulos, lambda s: pd.to_datetime(s, errors='coerce', format='mixed')) >= UMBRAL_RATIO_TIPO:
        return 'fecha'
    return 'categorico'


def analizar_columnas(df):
    """Para cada columna del archivo, determina su tipo y si es apta para usarse como valor
    (numérica) o como categoría de agrupación (texto/fecha con cardinalidad razonable) en una
    gráfica. `motivo_no_apta` explica por qué una columna no aparece en ninguna de las dos listas
    (para mostrarlo al usuario, no como un error)."""
    total_filas = len(df)
    columnas = []

    for nombre in df.columns:
        serie = df[nombre]
        sin_nulos = serie.dropna()
        valores_no_nulos = int(len(sin_nulos))
        valores_unicos = int(sin_nulos.nunique())

        if valores_no_nulos == 0:
            columnas.append({
                'nombre': str(nombre), 'tipo': 'vacio', 'valores_no_nulos': 0, 'valores_unicos': 0,
                'apta_para_valor': False, 'apta_para_categoria': False,
                'motivo_no_apta': 'La columna está vacía.',
            })
            continue

        tipo = _detectar_tipo(sin_nulos)
        apta_para_valor = tipo == 'numerico'
        apta_para_categoria = False
        motivo_no_apta = ''

        if not apta_para_valor:
            if valores_unicos <= 1:
                motivo_no_apta = 'Todos los valores son iguales.'
            elif total_filas > 1 and valores_unicos >= total_filas:
                motivo_no_apta = 'Todos los valores son distintos (parece un identificador).'
            elif valores_unicos > CARDINALIDAD_MAXIMA_CATEGORIA:
                motivo_no_apta = f'Tiene demasiados valores distintos ({valores_unicos}) para agrupar en una gráfica.'
            else:
                apta_para_categoria = True

        columnas.append({
            'nombre': str(nombre),
            'tipo': tipo,
            'valores_no_nulos': valores_no_nulos,
            'valores_unicos': valores_unicos,
            'apta_para_valor': apta_para_valor,
            'apta_para_categoria': apta_para_categoria,
            'motivo_no_apta': motivo_no_apta,
        })

    return {'total_filas': total_filas, 'columnas': columnas}


# Umbral de la advertencia de "columnas con valores en blanco recurrentes" (frontend,
# `TemplateMappingStep.jsx`) — una celda vacía suelta no amerita avisar; hacen falta al menos
# esta cantidad de filas en blanco en la misma columna.
UMBRAL_BLANCOS_RECURRENTES = 3


def columnas_con_blancos_recurrentes(df, umbral=UMBRAL_BLANCOS_RECURRENTES, cantidad_ejemplos=3):
    """Columnas cuyo valor viene en blanco (NaN) en `umbral` o más filas de `df` — no reporta
    columnas con menos blancos que eso. El tratamiento real de esos blancos (agrupados como "Sin
    dato" si la columna se usa como categoría, ignorados en la suma/promedio si se usa como valor)
    ya lo decide `analizar_columnas`/`generar_datos_*`; esta función solo detecta DÓNDE están, para
    que el frontend arme el aviso combinando ambas cosas.

    Por cada columna con blancos recurrentes, hasta `cantidad_ejemplos` filas de muestra: el
    número de fila tal como se vería en el archivo Excel original (contando la fila de
    encabezado) y los valores de las 2 primeras columnas del archivo (una referencia rápida para
    ubicar la fila sin tener que abrirlo)."""
    columnas_referencia = list(df.columns[:2])
    resultado = []
    for columna in df.columns:
        nulos = df[columna].isna()
        cantidad = int(nulos.sum())
        if cantidad < umbral:
            continue

        filas_ejemplo = []
        for indice in df.index[nulos][:cantidad_ejemplos]:
            fila = df.loc[indice]
            filas_ejemplo.append({
                'numero_fila': int(indice) + 2,  # +1 por índice 0-based, +1 por la fila de encabezado
                'referencia': {c: (None if pd.isna(fila[c]) else fila[c]) for c in columnas_referencia if c != columna},
            })

        resultado.append({'columna': str(columna), 'cantidad_en_blanco': cantidad, 'filas_ejemplo': filas_ejemplo})

    return resultado


def aplicar_seleccion_usuario(columnas, nombres_utilizables):
    """El análisis automático (`analizar_columnas`) es solo una sugerencia — el usuario decide,
    columna por columna, cuáles marcar como utilizables (ninguna se oculta ni se excluye por sí
    sola). Esto anula `apta_para_valor`/`apta_para_categoria` para cada columna: las marcadas
    quedan aptas según su tipo (numérica → valor, cualquier otro tipo → categoría); las no
    marcadas quedan inaptas para ambas, sin importar lo que haya sugerido el análisis."""
    nombres_utilizables = set(nombres_utilizables)
    resultado = []
    for columna in columnas:
        utilizable = columna['nombre'] in nombres_utilizables
        resultado.append({
            **columna,
            'apta_para_valor': utilizable and columna['tipo'] == 'numerico',
            'apta_para_categoria': utilizable and columna['tipo'] != 'numerico',
        })
    return resultado


MAX_CATEGORIAS_POR_VALOR = 3

# Catálogo de tipos de visualización disponibles para cualquier gráfica sugerida (sección
# "los gráficos sugeridos se pueden visualizar de cualquiera de estas formas"). `requiere_serie`
# marca los que necesitan una segunda columna de agrupación (barras agrupadas/apiladas) — solo
# están disponibles cuando la recomendación trae `columna_serie_sugerida`.
TIPOS_VISUALIZACION = [
    {'id': 'kpi', 'etiqueta': 'Tarjeta KPI', 'requiere_categoria': False, 'requiere_serie': False},
    {'id': 'barras_verticales', 'etiqueta': 'Barras verticales', 'requiere_categoria': True, 'requiere_serie': False},
    {'id': 'barras_horizontales', 'etiqueta': 'Barras horizontales', 'requiere_categoria': True, 'requiere_serie': False},
    {'id': 'barras_agrupadas', 'etiqueta': 'Barras agrupadas', 'requiere_categoria': True, 'requiere_serie': True},
    {'id': 'barras_apiladas', 'etiqueta': 'Barras apiladas', 'requiere_categoria': True, 'requiere_serie': True},
    {'id': 'area_apilada', 'etiqueta': 'Área apilada', 'requiere_categoria': True, 'requiere_serie': True},
    {'id': 'lineas', 'etiqueta': 'Líneas', 'requiere_categoria': True, 'requiere_serie': False},
    # Varias columnas de valor sobre un mismo eje de categorías (`generar_datos_multivalor`), no
    # una columna partida por una segunda categoría — usado por la plantilla fija de dashboard
    # ("Gráfico 2": comparar dos métricas, p. ej. ingresos vs. gastos, mes a mes).
    {'id': 'lineas_multiples', 'etiqueta': 'Líneas múltiples', 'requiere_categoria': True, 'requiere_serie': False},
    {'id': 'pastel', 'etiqueta': 'Pastel', 'requiere_categoria': True, 'requiere_serie': False},
    {'id': 'dona', 'etiqueta': 'Dona', 'requiere_categoria': True, 'requiere_serie': False},
    {'id': 'tabla', 'etiqueta': 'Tabla', 'requiere_categoria': True, 'requiere_serie': False},
    # A diferencia del resto, no agrupa por categoría: cada fila del archivo con ambas columnas
    # numéricas presentes es un punto (`generar_datos_dispersion`) — por eso no tiene
    # `requiere_categoria`/`requiere_serie` como los demás, y solo se ofrece a través de su propia
    # recomendación (ver `_mejor_par_columnas_numericas`), no como variante de una con categoría.
    {'id': 'dispersion', 'etiqueta': 'Dispersión', 'requiere_categoria': False, 'requiere_serie': False},
]


def _mejor_par_columnas_numericas(columnas_valor):
    """Elige, de forma determinista, las dos columnas numéricas con más datos (menos nulos) para
    proponer UNA gráfica de dispersión — igual criterio de acotar a una sola propuesta que
    `_mejor_columna_serie` (en vez de la combinación de todos los pares posibles, que crece en
    cuadrado con la cantidad de columnas numéricas). `None` si no hay al menos dos disponibles."""
    if len(columnas_valor) < 2:
        return None
    candidatas = sorted(columnas_valor, key=lambda c: c['valores_no_nulos'], reverse=True)
    return candidatas[0]['nombre'], candidatas[1]['nombre']


def _mejor_columna_serie(columnas, excluir_nombre):
    """Elige la mejor columna de categoría disponible para usar como segunda dimensión (serie) en
    una gráfica agrupada/apilada — la de menor cardinalidad, distinta de la ya usada como
    categoría principal. `None` si no hay ninguna otra disponible (esa recomendación simplemente
    no ofrece barras agrupadas/apiladas)."""
    candidatas = sorted(
        (c for c in columnas if c['apta_para_categoria'] and c['nombre'] != excluir_nombre),
        key=lambda c: c['valores_unicos'],
    )
    return candidatas[0]['nombre'] if candidatas else None


def generar_recomendaciones(columnas):
    """Propone qué gráficas armar a partir de las columnas ya analizadas (`analizar_columnas`):
    un KPI de total por cada columna numérica, y una gráfica por cada combinación razonable de
    columna numérica × columna de categoría (limitada a las `MAX_CATEGORIAS_POR_VALOR` categorías
    de menor cardinalidad, para no proponer decenas de combinaciones poco legibles). Cada
    recomendación con categoría trae además `columna_serie_sugerida` (la mejor segunda columna de
    agrupación disponible, o `None`), para que barras agrupadas/apiladas también sean una opción
    de visualización real. No calcula los datos todavía — eso ocurre recién al confirmar una
    recomendación (`generar_datos_grafica`/`generar_datos_multiserie`), para no procesar
    combinaciones que el usuario nunca va a pedir."""
    columnas_valor = [c for c in columnas if c['apta_para_valor']]
    columnas_categoria_todas = [c for c in columnas if c['apta_para_categoria']]
    columnas_categoria = sorted(columnas_categoria_todas, key=lambda c: c['valores_unicos'])[:MAX_CATEGORIAS_POR_VALOR]

    recomendaciones = []
    for columna_valor in columnas_valor:
        recomendaciones.append({
            'id': f"{columna_valor['nombre']}::total",
            'tipo_grafica': 'kpi',
            'columna_valor': columna_valor['nombre'],
            'columna_categoria': None,
            'categorias_unicas': None,
            'columna_serie_sugerida': None,
        })
        for columna_categoria in columnas_categoria:
            recomendaciones.append({
                'id': f"{columna_valor['nombre']}::{columna_categoria['nombre']}",
                'tipo_grafica': 'chart',
                'columna_valor': columna_valor['nombre'],
                'columna_categoria': columna_categoria['nombre'],
                'categorias_unicas': columna_categoria['valores_unicos'],
                'columna_serie_sugerida': _mejor_columna_serie(columnas_categoria_todas, columna_categoria['nombre']),
            })

    par_dispersion = _mejor_par_columnas_numericas(columnas_valor)
    if par_dispersion:
        columna_x, columna_y = par_dispersion
        recomendaciones.append({
            'id': f'{columna_x}::{columna_y}::dispersion',
            'tipo_grafica': 'dispersion',
            'columna_valor': columna_x,
            'columna_valor_y': columna_y,
            'columna_categoria': None,
            'categorias_unicas': None,
            'columna_serie_sugerida': None,
        })

    return recomendaciones


def calcular_datos_recomendaciones(df, recomendaciones):
    """Calcula los datos de cada recomendación (mismas funciones que se usan al confirmarla de
    verdad) para que el frontend pueda mostrar una vista previa real de cualquiera de sus formas
    de visualización disponibles antes de agregarla — no solo el título y la descripción. `datos`
    (y `datos_multiserie`, si aplica) quedan en `None` si la columna ya no existiera en el archivo
    (no debería pasar en circunstancias normales, pero no es un caso que deba romper la vista
    previa)."""
    resultado = []
    for r in recomendaciones:
        if r['tipo_grafica'] == 'dispersion':
            resultado.append({
                **r,
                'datos': generar_datos_dispersion(df, r['columna_valor'], r['columna_valor_y']),
                'datos_multiserie': None,
            })
            continue
        datos_multiserie = None
        if r.get('columna_serie_sugerida'):
            datos_multiserie = generar_datos_multiserie(df, r['columna_valor'], r['columna_categoria'], r['columna_serie_sugerida'])
        resultado.append({
            **r,
            'datos': generar_datos_grafica(df, r['columna_valor'], r['columna_categoria']),
            'datos_multiserie': datos_multiserie,
        })
    return resultado


def _agrupar_top_n(agrupado, limite=LIMITE_CATEGORIAS_EN_GRAFICA):
    if len(agrupado) <= limite:
        return agrupado
    top = agrupado.iloc[:limite]
    resto = float(agrupado.iloc[limite:].sum())
    if resto:
        top = pd.concat([top, pd.Series({'Otras': resto})])
    return top


def generar_conteo_valores_unicos(df, columna):
    """Cantidad de valores distintos (no nulos) de una columna — para un KPI de "conteo" en vez
    de "suma" (p. ej. cantidad de clientes o números de documento diferentes). A diferencia de
    `generar_datos_grafica`, no hace falta que la columna sea numérica: cuenta valores únicos de
    cualquier tipo (texto, ID, etc.)."""
    if columna not in df.columns:
        return None
    return {'tipo': 'kpi', 'valor': int(df[columna].dropna().nunique())}


def generar_promedio_columna(df, columna):
    """Promedio (media aritmética) de una columna numérica — para un KPI de "promedio" en vez de
    "suma" (p. ej. saldo promedio o días de crédito promedio). `None` si la columna no existe o no
    tiene ningún valor numérico, igual que el resto de agregaciones de KPI."""
    if columna not in df.columns:
        return None
    valores = pd.to_numeric(df[columna], errors='coerce').dropna()
    if valores.empty:
        return None
    return {'tipo': 'kpi', 'valor': round(float(valores.mean()), 2)}


LIMITE_VALORES_UNICOS_FILTRO = 500


def valores_unicos_de_columna(df, columna, limite=LIMITE_VALORES_UNICOS_FILTRO):
    """Valores distintos (no nulos, como texto, orden alfabético) de una columna — para poblar el
    selector "valor" del filtro opcional de una posición de la plantilla (`columna_filtro`/
    `valor_filtro`). `total` es la cantidad real de valores distintos, por si `limite` recortó la
    lista (columnas de altísima cardinalidad, p. ej. un identificador)."""
    if columna not in df.columns:
        return None
    valores = sorted(str(v) for v in df[columna].dropna().unique())
    return {'valores': valores[:limite], 'total': len(valores)}


def generar_datos_grafica(df, columna_valor, columna_categoria=None):
    """Agrega los datos de una gráfica a partir de una columna de valor (numérica, se suma) y,
    opcionalmente, una columna de categoría para agrupar. Sin categoría, el resultado es un único
    total (KPI); con categoría, una serie de barras (suma por categoría, top 15 + "Otras")."""
    if columna_valor not in df.columns:
        return None

    valores = pd.to_numeric(df[columna_valor], errors='coerce')

    if not columna_categoria:
        return {'tipo': 'kpi', 'valor': round(float(valores.sum()), 2)}

    if columna_categoria not in df.columns:
        return None

    categorias = df[columna_categoria].fillna('Sin dato').astype(str)
    agrupado = valores.groupby(categorias).sum().sort_values(ascending=False)
    agrupado = _agrupar_top_n(agrupado)

    return {
        'tipo': 'chart',
        'categorias': [str(c) for c in agrupado.index.tolist()],
        'valores': [round(float(v), 2) for v in agrupado.values.tolist()],
    }


MAX_SERIES_EN_GRAFICA = 6


def generar_datos_multiserie(df, columna_valor, columna_categoria, columna_serie):
    """Agrega los datos de una gráfica de barras agrupadas/apiladas: suma de `columna_valor` por
    cada combinación de `columna_categoria` (eje) × `columna_serie` (una barra/segmento por cada
    valor distinto de esta columna). Limita las categorías igual que `generar_datos_grafica` (top
    15 + "Otras") y las series a las `MAX_SERIES_EN_GRAFICA` de mayor total, para no saturar la
    leyenda con decenas de segmentos apenas visibles."""
    if columna_valor not in df.columns or columna_categoria not in df.columns or columna_serie not in df.columns:
        return None

    valores = pd.to_numeric(df[columna_valor], errors='coerce')
    categorias = df[columna_categoria].fillna('Sin dato').astype(str)
    series = df[columna_serie].fillna('Sin dato').astype(str)

    tabla_completa = valores.groupby([categorias, series]).sum().unstack(fill_value=0.0)

    totales_categoria = tabla_completa.sum(axis=1).sort_values(ascending=False)
    if len(totales_categoria) > LIMITE_CATEGORIAS_EN_GRAFICA:
        categorias_incluidas = totales_categoria.index[:LIMITE_CATEGORIAS_EN_GRAFICA]
        tabla = tabla_completa.loc[categorias_incluidas]
        # Las categorías fuera del top se agrupan en "Otras", sumando cada serie por separado.
        resto = tabla_completa.drop(index=categorias_incluidas)
        if not resto.empty:
            tabla.loc['Otras'] = resto.sum(axis=0)
    else:
        tabla = tabla_completa

    totales_serie = tabla.sum(axis=0).sort_values(ascending=False)
    series_incluidas = totales_serie.index[:MAX_SERIES_EN_GRAFICA]
    tabla = tabla[series_incluidas]

    return {
        'tipo': 'multiserie',
        'categorias': [str(c) for c in tabla.index.tolist()],
        'series': [
            {'nombre': str(s), 'valores': [round(float(v), 2) for v in tabla[s].tolist()]}
            for s in tabla.columns
        ],
    }


LIMITE_PUNTOS_DISPERSION = 300


def generar_datos_dispersion(df, columna_x, columna_y):
    """Calcula los puntos (x, y) de una gráfica de dispersión a partir de dos columnas numéricas —
    a diferencia del resto de gráficas, no agrupa por categoría: cada fila del archivo con ambos
    valores presentes es un punto. Se limita a `LIMITE_PUNTOS_DISPERSION` filas (las primeras del
    archivo, muestra determinista) para no saturar el gráfico ni la respuesta con archivos de
    miles de filas."""
    if columna_x not in df.columns or columna_y not in df.columns:
        return None

    x = pd.to_numeric(df[columna_x], errors='coerce')
    y = pd.to_numeric(df[columna_y], errors='coerce')
    validos = pd.DataFrame({'x': x, 'y': y}).dropna()
    if len(validos) > LIMITE_PUNTOS_DISPERSION:
        validos = validos.iloc[:LIMITE_PUNTOS_DISPERSION]

    return {
        'tipo': 'dispersion',
        'puntos': [{'x': round(float(fila.x), 2), 'y': round(float(fila.y), 2)} for fila in validos.itertuples()],
    }


def generar_datos_multivalor(df, columna_categoria, columnas_valor):
    """Agrega los datos de una gráfica que compara varias métricas (columnas de valor distintas)
    sobre un mismo eje de categorías — a diferencia de `generar_datos_multiserie` (una sola
    columna de valor partida por una segunda columna de categoría), aquí cada serie es una
    columna numérica distinta ya existente en el archivo (p. ej. "Ingresos" vs. "Gastos" por
    mes). Mismo shape de salida (`{tipo: 'multiserie', categorias, series}`) que
    `generar_datos_multiserie`, para reutilizar los mismos componentes de renderizado (líneas
    múltiples, barras agrupadas/apiladas, área apilada)."""
    if columna_categoria not in df.columns or not columnas_valor:
        return None
    if any(c not in df.columns for c in columnas_valor):
        return None

    categorias = df[columna_categoria].fillna('Sin dato').astype(str)
    agrupados = {c: pd.to_numeric(df[c], errors='coerce').groupby(categorias).sum() for c in columnas_valor}

    totales_categoria = agrupados[columnas_valor[0]].sort_values(ascending=False)
    hay_resto = len(totales_categoria) > LIMITE_CATEGORIAS_EN_GRAFICA
    categorias_incluidas = totales_categoria.index[:LIMITE_CATEGORIAS_EN_GRAFICA] if hay_resto else totales_categoria.index

    series = []
    for columna in columnas_valor:
        agrupado = agrupados[columna]
        incluidos = [round(float(v), 2) for v in agrupado.reindex(categorias_incluidas, fill_value=0.0).tolist()]
        if hay_resto:
            resto = float(agrupado.drop(index=categorias_incluidas, errors='ignore').sum())
            incluidos.append(round(resto, 2))
        series.append({'nombre': str(columna), 'valores': incluidos})

    categorias_finales = [str(c) for c in categorias_incluidas.tolist()]
    if hay_resto:
        categorias_finales.append('Otras')

    return {'tipo': 'multiserie', 'categorias': categorias_finales, 'series': series}


TIPOS_AGREGACION_TABLA = ('suma', 'promedio', 'conteo_unicos', 'valor_celda')


def normalizar_columna_valor_tabla(columna_valor):
    """Cada entrada de `columnas_valor` es `{'columna': str, 'tipo_agregacion': 'suma'|'promedio'|
    'conteo_unicos'|'valor_celda'}` (sección 23) — también acepta el string plano de antes de esa
    sección (tratado como 'suma'), para que una tabla mapeada antes de este cambio se siga pudiendo
    recalcular sin que el usuario tenga que rehacer el mapeo. Público (no `_`): también lo usa
    `services/historico.py` para normalizar las columnas de una tabla histórica (sección 28)."""
    if columna_valor is None:
        return {'columna': None, 'tipo_agregacion': 'suma'}
    if isinstance(columna_valor, str):
        return {'columna': columna_valor, 'tipo_agregacion': 'suma'}
    tipo = columna_valor.get('tipo_agregacion')
    return {'columna': columna_valor.get('columna'), 'tipo_agregacion': tipo if tipo in TIPOS_AGREGACION_TABLA else 'suma'}


def _valor_celda(serie):
    """Para el tipo de agregación 'valor_celda': en vez de sumar/promediar, muestra el valor real
    de la celda cuando todas las filas del grupo comparten el mismo (columnas que identifican algo
    y no varían entre filas de un mismo grupo, p. ej. "Zona" o "Ciudad" de un cliente) — si
    difieren, no hay un único valor que mostrar, así que devuelve 'Varios' en vez de elegir uno al
    azar. `None` cuando el grupo no tiene ningún valor no nulo."""
    valores = serie.dropna().unique()
    if len(valores) == 0:
        return None
    if len(valores) == 1:
        return valores[0]
    return 'Varios'


def valor_agregado(serie, tipo_agregacion):
    """Aplica el tipo de agregación elegido a una columna de valor: 'suma' (agrega
    montos/cantidades), 'promedio' (media aritmética), 'conteo_unicos' (cuenta valores distintos —
    sirve para columnas no numéricas, p. ej. cuántos clientes o documentos distintos hay) o
    'valor_celda' (el valor real de la celda si es el mismo en toda la serie, ver `_valor_celda`).
    Público (no `_`): también lo usa `services/historico.py` para agregar una columna a través de
    varias cargas (sección 28), no solo dentro de un mismo archivo."""
    if tipo_agregacion == 'conteo_unicos':
        return serie.nunique()
    if tipo_agregacion == 'valor_celda':
        return _valor_celda(serie)
    numerica = pd.to_numeric(serie, errors='coerce')
    return numerica.mean() if tipo_agregacion == 'promedio' else numerica.sum()


def generar_datos_tabla(df, columna_id, columnas_valor, limite=LIMITE_FILAS_TABLA):
    """Arma una tabla con una fila por cada valor de `columna_id` (las `limite` de mayor total en
    la primera columna de valor — un tope de seguridad alto, no la cantidad a mostrar: eso lo
    decide el frontend con su propio paginador, sección 24), una columna por cada entrada de
    `columnas_valor` — cada una agregada con el tipo de cálculo que el usuario haya elegido para
    esa columna (`suma`, `promedio`, `conteo_unicos` o `valor_celda`, sección 23) —, una columna
    final de "% del total" (sobre la primera columna de valor, agregada del mismo modo) y una fila
    de totales: siempre la suma de lo que se ve en cada columna, sin importar su tipo de agregación
    (así "Total" significa lo mismo en toda la tabla: la suma de las filas mostradas). A diferencia
    de una comparación "vs. mes anterior", el % del total siempre se puede calcular sin necesitar
    una dimensión de tiempo en el archivo.

    `valor_celda` es la excepción a "todo es una cantidad": es texto/categoría, no algo que se
    pueda sumar ni rankear numéricamente. Si la PRIMERA columna de valor es `valor_celda`, el orden
    de las filas queda alfabético (no por magnitud) y "% del total" queda en 0 para todas las filas
    (no hay total numérico contra el cual repartir un porcentaje); si cualquier otra columna lo es,
    su celda en la fila de "Total" queda vacía (`None`) en vez de intentar sumar texto."""
    if columna_id not in df.columns or not columnas_valor:
        return None
    entradas = [normalizar_columna_valor_tabla(c) for c in columnas_valor]
    if any(e['columna'] not in df.columns for e in entradas):
        return None

    identidad = df[columna_id].fillna('Sin dato').astype(str)

    def agrupado(entrada):
        nombre_columna, tipo = entrada['columna'], entrada['tipo_agregacion']
        if tipo == 'conteo_unicos':
            return df[nombre_columna].groupby(identidad).nunique()
        if tipo == 'valor_celda':
            return df[nombre_columna].groupby(identidad).agg(_valor_celda)
        numerica = pd.to_numeric(df[nombre_columna], errors='coerce')
        return numerica.groupby(identidad).mean() if tipo == 'promedio' else numerica.groupby(identidad).sum()

    # Listas posicionales (no un dict por nombre de columna): la misma columna origen puede
    # aparecer más de una vez con un tipo de agregación distinto en cada una (p. ej. "Ventas -
    # Suma" y "Ventas - Promedio" como dos columnas separadas de la tabla) y cada aparición debe
    # mantener su propio cálculo, no fundirse con las demás.
    agrupados = [agrupado(e) for e in entradas]

    primaria_numerica = entradas[0]['tipo_agregacion'] != 'valor_celda'
    principal = agrupados[0]
    top_ids = principal.sort_values(ascending=False).index[:limite]
    total_general = float(valor_agregado(df[entradas[0]['columna']], entradas[0]['tipo_agregacion'])) if primaria_numerica else 0.0

    filas = []
    totales_por_columna = [(0.0 if e['tipo_agregacion'] != 'valor_celda' else None) for e in entradas]
    for nombre_id in top_ids:
        fila = [str(nombre_id)]
        for i, (entrada, serie_agrupada) in enumerate(zip(entradas, agrupados)):
            valor_bruto = serie_agrupada.get(nombre_id)
            if entrada['tipo_agregacion'] == 'valor_celda':
                fila.append(valor_bruto if pd.notna(valor_bruto) else None)
            else:
                valor = float(valor_bruto) if pd.notna(valor_bruto) else 0.0
                fila.append(round(valor, 2))
                totales_por_columna[i] += valor
        valor_principal = float(principal.get(nombre_id, 0.0)) if primaria_numerica else 0.0
        porcentaje = round((valor_principal / total_general * 100) if (primaria_numerica and total_general) else 0.0, 2)
        fila.append(porcentaje)
        filas.append(fila)

    fila_total = ['Total'] + [(round(total, 2) if total is not None else None) for total in totales_por_columna]
    porcentaje_total = round((totales_por_columna[0] / total_general * 100) if (primaria_numerica and total_general) else 0.0, 2)
    fila_total.append(porcentaje_total)

    return {
        'tipo': 'tabla_multi',
        'columnas': [str(columna_id)] + [str(e['columna']) for e in entradas] + ['% del total'],
        'filas': filas,
        'total': fila_total,
    }
