"""Réplica de la pestaña "6. Cartera" del informe financiero mensual (`Mockup_Directorio_Cartera`).

Este dashboard es la excepción declarada del proyecto: no usa las 13 posiciones de la plantilla
genérica ni sus renderers. Cada sección del mockup tiene una forma propia que los componentes
genéricos no saben dibujar —etiquetas sobre las barras, una columna de meta con ✓/✗, tarjetas
resumen dentro de una sección, mini-tablas por deudor—, así que el contenido se arma acá con una
forma propia (`content['bloque']`) y lo dibuja `components/dashboard-directorio/` en el frontend.
El despacho es `config['render'] == 'directorio'`; ningún otro dashboard lo lleva.

Secciones (en el orden del mockup):
1. Cuatro KPI de cabecera, cada uno con su subtítulo de contexto.
2. Antigüedad de cartera por tramos, con el monto y el % sobre cada barra.
3. Cumplimiento de metas de antigüedad (acumulado), con la meta al lado del valor.
4. Concentración: Top N vs. resto, con dos tarjetas resumen y el detalle cliente por cliente.
5. Antigüedad de los dos mayores deudores, uno al lado del otro.

El "Anexo — evolución del saldo" del mockup NO está: necesita el saldo del cliente al cierre de
cada mes, y un corte de cobranza es una foto única. El propio mockup lo dice en su nota (esos
números vienen del informe de posición de caja, otro archivo). Inventarlos sería fabricar cifras
financieras.
"""

import pandas as pd

from ..models import DashboardComponent, DashboardLayout
from . import dashboard_layout, generic_charts

IDS_FABRICA = [
    'kpi-1', 'kpi-2', 'kpi-3', 'kpi-4',
    'grafico-1', 'grafico-2', 'grafico-3', 'grafico-4', 'grafico-5', 'grafico-6',
    'tabla-1', 'tabla-2', 'tabla-3',
]

COLUMNA_VALOR = 'Saldo'
COLUMNA_FECHA = 'Fecha de Vencimiento'
COLUMNA_CLIENTE = 'Cliente'

DORADO, VERDE, AZUL = '#D4AF37', '#2E7D32', '#1E88E5'
ROJO, GRANATE, CORAL, ROSA = '#C62828', '#8B1E1E', '#EF9A9A', '#F48FB1'

TRAMOS = ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días']
COLORES_TRAMOS = [VERDE, AZUL, DORADO, CORAL, ROSA, ROJO]

# Metas del mockup: las cinco primeras filas son acumuladas y se exigen crecientes; la última es la
# cola >120 días, que se acota por arriba.
METAS = [
    {'etiqueta': '≥ 50%', 'minimo': 50}, {'etiqueta': '≥ 70%', 'minimo': 70},
    {'etiqueta': '≥ 80%', 'minimo': 80}, {'etiqueta': '≥ 90%', 'minimo': 90},
    {'etiqueta': '≥ 95%', 'minimo': 95}, {'etiqueta': '≤ 5%', 'maximo': 5},
]
ETIQUETAS_ACUMULADAS = [
    'Corriente', 'Vencido ≤ 30 días (acum.)', 'Vencido ≤ 60 días (acum.)',
    'Vencido ≤ 90 días (acum.)', 'Vencido ≤ 120 días (acum.)', 'Más de 120 días',
]

TOP_N = 16
DIAS_MAS_DE_120 = 120

_MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]


def columnas_requeridas():
    return [COLUMNA_VALOR, COLUMNA_FECHA, COLUMNA_CLIENTE]


def columnas_faltantes(df):
    return [columna for columna in columnas_requeridas() if columna not in df.columns]


def _periodo(fecha):
    return f'{_MESES[fecha.month - 1]} {fecha.year}'


def _porcentaje(parte, total):
    return round(parte / total * 100, 2) if total else 0.0


def _compacto(valor):
    """`$2116K`, como en el mockup: miles con K, sin decimales y sin separador de miles."""
    return f'${valor / 1000:.0f}K'


def _miles(valor, decimales=0):
    """`3,139,563` — el separador de miles del informe, el mismo que usa el frontend.

    Se aplica SOLO al número. Antes esto se resolvía con un `.replace(',', '.')` sobre la frase
    entera, que se llevaba puestas las comas de la redacción: "del saldo, con un ticket" terminaba
    escrito como "del saldo. con un ticket".
    """
    return f'{valor:,.{decimales}f}'


def _saldos(df):
    return pd.to_numeric(df[COLUMNA_VALOR], errors='coerce')


def _dias_vencidos(df, fecha_corte):
    return generic_charts.dias_transcurridos_desde(df[COLUMNA_FECHA], fecha_corte)


# --- Secciones ---------------------------------------------------------------

def _kpis(df, fecha_corte):
    saldos = _saldos(df)
    dias = _dias_vencidos(df, fecha_corte)
    total = float(saldos.sum())
    corriente = float(saldos[(dias <= 0).fillna(False)].sum())
    vencida = float(saldos[(dias > 0).fillna(False)].sum())
    mas_120 = float(saldos[(dias > DIAS_MAS_DE_120).fillna(False)].sum())
    pct_mas_120 = _porcentaje(mas_120, total)
    maximo = METAS[-1]['maximo']

    return [
        {
            'component_id': 'cartera-total', 'etiqueta': 'CARTERA TOTAL (CORTE COBRANZA)',
            'valor': total, 'subtitulo': f'Corte {_periodo(fecha_corte)}', 'tono': 'neutro', 'color': DORADO,
        },
        {
            'component_id': 'al-corriente', 'etiqueta': 'AL CORRIENTE (ANTICIPADA)',
            'valor': corriente, 'subtitulo': f'{_porcentaje(corriente, total):.0f}% del portafolio',
            'tono': 'neutro', 'color': VERDE,
        },
        {
            'component_id': 'vencida-total', 'etiqueta': 'VENCIDA TOTAL',
            'valor': vencida, 'subtitulo': f'{_porcentaje(vencida, total):.0f}% del portafolio',
            'tono': 'alerta', 'color': ROJO,
        },
        {
            'component_id': 'vencida-mas-120-dias', 'etiqueta': 'VENCIDA +120 DÍAS', 'valor': mas_120,
            'subtitulo': (
                f'▲ {pct_mas_120:.0f}% · excede meta máx. {maximo}%' if pct_mas_120 > maximo
                else f'{pct_mas_120:.0f}% · dentro de la meta máx. {maximo}%'
            ),
            'tono': 'alerta' if pct_mas_120 > maximo else 'ok', 'color': GRANATE,
        },
    ]


def _antiguedad(df, fecha_corte):
    datos = generic_charts.generar_datos_tramos_antiguedad(df, COLUMNA_FECHA, COLUMNA_VALOR, fecha_corte)
    if not datos:
        return None
    valores = [float(v) for v in datos['valores']]
    total = sum(valores)
    # El monto y el % van SOBRE la barra, como en el mockup: la altura sola no deja leer un tramo
    # de 10K al lado de uno de 2.100K.
    etiquetas = [f'{_compacto(v)} ({_porcentaje(v, total):.0f}%)' for v in valores]

    mayor = max(range(len(valores)), key=lambda i: valores[i])
    cola = valores[-1]
    return {
        'bloque': 'antiguedad', 'titulo': f'ANTIGÜEDAD DE CARTERA — {_periodo(fecha_corte).upper()}',
        'categorias': list(datos['categorias']), 'valores': valores,
        'etiquetas': etiquetas, 'colores': list(COLORES_TRAMOS),
        'hallazgos': (
            f'El {_porcentaje(valores[0], total):.0f}% de la cartera está al corriente (anticipada) y el '
            f'{_porcentaje(valores[1], total):.0f}% adicional está en el tramo 30 días. El tramo más pesado es '
            f'**{datos["categorias"][mayor]}** con {_compacto(valores[mayor])}. La cola "+120 días" concentra '
            f'**{_compacto(cola)} ({_porcentaje(cola, total):.0f}%)** del total.'
        ),
    }


def _cumplimiento(df, fecha_corte):
    datos = generic_charts.generar_datos_cumplimiento_tramos(
        df, COLUMNA_FECHA, COLUMNA_VALOR,
        [{'meta_min': m['minimo']} if 'minimo' in m else {'meta_max': m['maximo']} for m in METAS],
        fecha_corte,
    )
    if not datos:
        return None

    filas = []
    for i, fila in enumerate(datos['filas']):
        _etiqueta, valor, porcentaje, _resultado = fila
        meta = METAS[i]
        cumple = porcentaje >= meta['minimo'] if 'minimo' in meta else porcentaje <= meta['maximo']
        filas.append({
            'edad': ETIQUETAS_ACUMULADAS[i], 'meta': meta['etiqueta'],
            'valor': float(valor), 'porcentaje': float(porcentaje), 'cumple': bool(cumple),
            'es_cola': i == len(METAS) - 1,
        })

    incumplidas = [f['edad'] for f in filas if not f['cumple']]
    return {
        'bloque': 'cumplimiento', 'titulo': 'CUMPLIMIENTO DE METAS DE ANTIGÜEDAD (ACUMULADO)',
        'columnas': ['EDAD DE CARTERA', 'META (MÍN./MÁX.)', 'VALOR ACUMULADO', 'RESULTADO'],
        'filas': filas,
        'nota': (
            'Las cinco primeras filas son acumuladas: cada una incluye a las anteriores. La última NO '
            'es una fila de cierre al 100%, es la cola ">120 días" sola. El acumulado ≤120 más esa cola '
            'dan 100%. La base del porcentaje es el total de filas que entraron en algún tramo: una fila '
            'sin fecha de vencimiento legible queda fuera de todos.'
            + (f' Tramos fuera de meta: {", ".join(incumplidas)}.' if incumplidas else ' Todos los tramos cumplen su meta.')
        ),
    }


def _concentracion(df, fecha_corte):
    saldos = _saldos(df)
    total = float(saldos.sum())
    por_cliente = saldos.groupby(df[COLUMNA_CLIENTE].astype(str).str.strip()).sum().sort_values(ascending=False)
    top = por_cliente.head(TOP_N)
    resto = por_cliente.iloc[TOP_N:]

    filas = []
    acumulado = 0.0
    for cliente, saldo in top.items():
        porcentaje = _porcentaje(float(saldo), total)
        acumulado = round(acumulado + porcentaje, 2)
        filas.append([cliente, float(saldo), porcentaje, acumulado])

    saldo_resto = float(resto.sum())
    pct_resto = _porcentaje(saldo_resto, total)
    saldo_top = float(top.sum())
    pct_top = _porcentaje(saldo_top, total)
    ticket = saldo_resto / len(resto) if len(resto) else 0.0

    return {
        'bloque': 'concentracion',
        'titulo': f'CONCENTRACIÓN DE CARTERA — TOP {TOP_N} CLIENTES VS. RESTO DE LA CARTERA',
        'resumen': [
            {'etiqueta': f'TOP {TOP_N} CLIENTES', 'valor': saldo_top,
             'subtitulo': f'{pct_top:.2f}% del saldo total', 'color': DORADO},
            {'etiqueta': f'RESTO ({_miles(len(resto))} CLIENTES)', 'valor': saldo_resto,
             'subtitulo': f'{pct_resto:.2f}% del saldo total', 'color': AZUL},
        ],
        'columnas': ['CLIENTE', 'SALDO', '% SOBRE TOTAL', '% ACUMULADO (CALCULADO)'],
        'filas': filas,
        'fila_resto': [f'Resto ({_miles(len(resto))} clientes)', saldo_resto, pct_resto, 100.0],
        'fila_total': ['TOTAL CARTERA', total, 100.0, None],
        'hallazgos': (
            f'La cartera está atomizada fuera de los {TOP_N} principales: **{_miles(len(resto))} clientes** '
            f'se reparten el {pct_resto:.2f}% restante del saldo, con un ticket promedio de '
            f'~${_miles(ticket)} por cliente — lo que limita el impacto de una gestión de cobranza '
            f'concentrada y sugiere priorizar los {TOP_N} clientes principales como palanca de '
            f'recuperación de caja más eficiente.'
        ),
        'nota': (
            'El "% acumulado" se recalcula acá como suma progresiva del "% sobre total"; el archivo '
            'fuente trae una columna homónima que en realidad repite el "% sobre total" fila por fila.'
        ),
    }


def _deudores(df, fecha_corte, cuantos=2):
    saldos = _saldos(df)
    total = float(saldos.sum())
    clientes = df[COLUMNA_CLIENTE].astype(str).str.strip()
    mayores = saldos.groupby(clientes).sum().sort_values(ascending=False).head(cuantos)

    deudores = []
    for nombre, saldo_cliente in mayores.items():
        del_cliente = df[clientes == nombre]
        datos = generic_charts.generar_datos_tramos_antiguedad(
            del_cliente, COLUMNA_FECHA, COLUMNA_VALOR, fecha_corte,
        )
        valores = [float(v) for v in datos['valores']] if datos else []
        suma = sum(valores)
        # Solo los tramos con saldo: el mockup no lista tramos vacíos.
        filas = [
            {'tramo': categoria, 'saldo': valor, 'porcentaje': _porcentaje(valor, suma)}
            for categoria, valor in zip(datos['categorias'], valores) if valor
        ] if datos else []
        peor = max(filas, key=lambda f: f['saldo']) if filas else None
        deudores.append({
            'nombre': nombre, 'saldo': float(saldo_cliente),
            'porcentaje_cartera': _porcentaje(float(saldo_cliente), total),
            'columnas': ['TRAMO', 'SALDO', '%'], 'filas': filas,
            'tramo_destacado': peor['tramo'] if peor else None,
            'comentario': (
                f'El {peor["porcentaje"]:.0f}% del saldo de este cliente está en "{peor["tramo"]}".'
                if peor else 'Sin tramos con saldo.'
            ),
        })

    return {
        'bloque': 'deudores',
        'titulo': f'ANTIGÜEDAD DE CARTERA — DOS MAYORES DEUDORES ({_periodo(fecha_corte).upper()})',
        'deudores': deudores,
        'hallazgos': (
            'Los dos mayores deudores concentran **'
            f'{sum(d["porcentaje_cartera"] for d in deudores):.2f}%** de la cartera total. Comparar en qué '
            'tramo está cada uno distingue una mora crónica (peso en "+120 días", requiere renegociación '
            'o vía legal) de una mora reciente (peso en 30–60 días, requiere cobranza inmediata antes de '
            'que escale).'
        ),
        'fuente': (
            f'Reporte de cartera por antigüedad y cliente al corte de {_periodo(fecha_corte)}, filtrado a '
            f'los {cuantos} mayores deudores (suma de ambos: ${_miles(sum(d["saldo"] for d in deudores))}).'
        ),
    }


# --- Composición del layout --------------------------------------------------

ANCHO_KPI, ALTO_KPI = 3, 170
ANCHO_PANEL, ALTO_ANTIGUEDAD, ALTO_CUMPLIMIENTO = 6, 560, 560
ALTO_CONCENTRACION, ALTO_DEUDORES = 900, 520


def construir_contenidos(df, fecha_corte):
    """Contenido de todas las secciones, sin tocar la base. Devuelve `[(spec, content)]`."""
    piezas = []

    for kpi in _kpis(df, fecha_corte):
        piezas.append((
            {'component_id': kpi['component_id'], 'type': 'kpi', 'chart_type': '',
             'width': ANCHO_KPI, 'height': ALTO_KPI, 'styles': {'colorPrincipal': kpi['color']}},
            {'bloque': 'kpi', 'titulo': kpi['etiqueta'], 'etiqueta': kpi['etiqueta'],
             'valor': kpi['valor'], 'subtitulo': kpi['subtitulo'], 'tono': kpi['tono'],
             'color': kpi['color']},
        ))

    secciones = [
        ('antiguedad-de-cartera', _antiguedad(df, fecha_corte), ANCHO_PANEL, ALTO_ANTIGUEDAD, 'barras_verticales'),
        ('cumplimiento-metas-antiguedad', _cumplimiento(df, fecha_corte), ANCHO_PANEL, ALTO_CUMPLIMIENTO, 'tabla'),
        ('concentracion-de-cartera', _concentracion(df, fecha_corte), 12, ALTO_CONCENTRACION, 'tabla'),
        ('mayores-deudores', _deudores(df, fecha_corte), 12, ALTO_DEUDORES, 'tabla'),
    ]
    for component_id, contenido, ancho, alto, chart_type in secciones:
        if contenido is None:
            continue
        contenido = {**contenido, 'titulo': contenido['titulo']}
        piezas.append((
            {'component_id': component_id, 'type': 'chart', 'chart_type': chart_type,
             'width': ancho, 'height': alto, 'styles': {}},
            contenido,
        ))

    return piezas


def _componentes_de_fabrica_ocultos(layout, orden_desde):
    """Las 13 posiciones de la plantilla, ocultas y bloqueadas, conservando todo lo demás.

    Se conservan en vez de borrarse para no perder su mapeo: volver al dashboard genérico es solo
    volver a mostrarlas.
    """
    componentes = []
    for i, componente in enumerate(layout.components.filter(component_id__in=IDS_FABRICA).order_by('order')):
        componentes.append({
            'component_id': componente.component_id, 'type': componente.type,
            'chart_type': componente.chart_type, 'row': 1, 'order': orden_desde + i,
            'width': componente.width, 'height': componente.height, 'is_visible': False,
            'content': componente.content or {}, 'styles': componente.styles or {},
            'config': {**(componente.config or {}), 'bloqueado': True},
            'mapeo': componente.mapeo or {},
        })
    return componentes


def construir(dashboard_id, df, fecha_corte):
    """Recalcula todas las secciones contra `df` y reescribe el layout completo."""
    layout = dashboard_layout.obtener_o_crear_layout(dashboard_id)
    piezas = construir_contenidos(df, fecha_corte)

    componentes = []
    for orden, (spec, contenido) in enumerate(piezas, start=1):
        componentes.append({
            'component_id': spec['component_id'], 'type': spec['type'],
            'chart_type': spec['chart_type'], 'row': 1, 'order': orden,
            'width': spec['width'], 'height': spec['height'], 'is_visible': True,
            'content': contenido, 'styles': spec['styles'],
            # `render: directorio` es lo que hace que el frontend use los componentes a medida de
            # este dashboard en vez de los genéricos; `bloqueado` impide que un usuario no
            # superusuario mueva, redimensione, oculte o borre una sección del informe.
            'config': {'zona': 'personal', 'bloqueado': True, 'render': 'directorio'},
            'mapeo': {},
        })

    componentes.extend(_componentes_de_fabrica_ocultos(layout, len(componentes) + 1))

    dashboard_layout._escribir_componentes(layout, componentes)
    layout.version += 1
    layout.save(update_fields=['version', 'actualizado_en'])
    return [spec['component_id'] for spec, _ in piezas]


def esta_sembrado(dashboard_id):
    layout = DashboardLayout.objects.filter(dashboard_id=dashboard_id).first()
    if layout is None:
        return False
    return DashboardComponent.objects.filter(layout=layout, component_id='cartera-total').exists()
