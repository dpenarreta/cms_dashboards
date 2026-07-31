"""Análisis genérico de columnas de un archivo cargado, recomendación de gráficas a partir de ese
análisis, y cálculo de los datos de cada gráfica confirmada — a diferencia del resto del paquete
`services/` (column_mapper, ingest, calculator, aggregations), este módulo no asume ningún esquema
de negocio fijo (cliente/saldo/causal/...): se aplica a cualquier archivo subido a cualquier
dashboard. Flujo: cargar archivo → analizar columnas (con alias editables en el frontend) →
recomendar gráficas → el usuario agrega, una por una, las que le sirven."""

import pandas as pd

CARDINALIDAD_MAXIMA_CATEGORIA = 50
LIMITE_CATEGORIAS_EN_GRAFICA = 15
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
