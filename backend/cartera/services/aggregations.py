"""Agregaciones para gráficos y tablas del dashboard (sección 10 de la especificación).

Recibe siempre un DataFrame ya filtrado por los filtros globales (sección 12) y la fecha de
corte vigente; las clasificaciones vencida/no vencida se recalculan aquí mismo con
`calculator.anotar_estado_y_mora` para que cualquier cambio de fecha de corte se refleje sin
tener que reprocesar el archivo.
"""

from ..utils.normalization import SIN_GESTION
from .calculator import anotar_estado_y_mora

TOP_CAUSALES_VISIBLES = 8


def top_clientes(df, fecha_corte, cartera_total, top_n=10):
    df = anotar_estado_y_mora(df, fecha_corte)
    if df.empty:
        return []

    grupos = df.groupby('identificador_cliente')
    filas = []
    for identificador, grupo in grupos:
        saldo_total = float(grupo['saldo'].sum())
        saldo_vencido = float(grupo.loc[grupo['estado_calculado'] == 'VENCIDA', 'saldo'].sum())
        saldo_no_vencido = float(grupo.loc[grupo['estado_calculado'] == 'NO VENCIDA', 'saldo'].sum())
        filas.append({
            'identificador_cliente': identificador,
            'cliente': next((c for c in grupo['cliente'] if c), '') or grupo['cliente'].iloc[0],
            'ruc_cliente': next((r for r in grupo['ruc_cliente'] if r), ''),
            'saldo_total': round(saldo_total, 2),
            'saldo_vencido': round(saldo_vencido, 2),
            'saldo_no_vencido': round(saldo_no_vencido, 2),
            'documentos': int(grupo['numero_documento'].nunique()),
            'porcentaje_sobre_total': round((saldo_total / cartera_total * 100) if cartera_total else 0.0, 2),
        })

    filas.sort(key=lambda f: f['saldo_total'], reverse=True)
    return filas[:top_n]


TOP_CIUDADES_VISIBLES = 8
OTRAS_CIUDADES = 'OTRAS CIUDADES'


def pareto_ciudades(df, fecha_corte, agrupar_otras=False):
    """Cartera vencida agrupada por ciudad (sección 10.2). Se usa tanto para el gráfico de
    pastel como, con `agrupar_otras`, para colapsar las ciudades de menor participación en una
    categoría 'OTRAS CIUDADES' consultable (sección 4 del drill-down)."""
    df = anotar_estado_y_mora(df, fecha_corte)
    vencida = df[(df['estado_calculado'] == 'VENCIDA')]
    if vencida.empty:
        return {'ciudades': [], 'total_vencida': 0.0}

    total_vencida = float(vencida['saldo'].sum())
    grupos = vencida.groupby('ciudad').agg(
        saldo_vencido=('saldo', 'sum'),
        documentos=('numero_documento', 'nunique'),
        clientes=('identificador_cliente', 'nunique'),
    ).reset_index()
    grupos['saldo_vencido'] = grupos['saldo_vencido'].astype(float)
    grupos = grupos.sort_values('saldo_vencido', ascending=False).reset_index(drop=True)
    grupos['porcentaje'] = grupos['saldo_vencido'] / total_vencida * 100 if total_vencida else 0.0
    grupos['porcentaje_acumulado'] = grupos['porcentaje'].cumsum()

    detalle = [
        {
            'ciudad': row.ciudad,
            'saldo_vencido': round(row.saldo_vencido, 2),
            'porcentaje': round(row.porcentaje, 2),
            'porcentaje_acumulado': round(row.porcentaje_acumulado, 2),
            'documentos': int(row.documentos),
            'clientes': int(row.clientes),
        }
        for row in grupos.itertuples()
    ]

    resultado = {'ciudades': detalle, 'total_vencida': round(total_vencida, 2)}

    if agrupar_otras and len(detalle) > TOP_CIUDADES_VISIBLES:
        principales = detalle[:TOP_CIUDADES_VISIBLES]
        resto = detalle[TOP_CIUDADES_VISIBLES:]
        otras = {
            'ciudad': OTRAS_CIUDADES,
            'saldo_vencido': round(sum(c['saldo_vencido'] for c in resto), 2),
            'porcentaje': round(sum(c['porcentaje'] for c in resto), 2),
            'porcentaje_acumulado': 100.0,
            'documentos': sum(c['documentos'] for c in resto),
            'clientes': sum(c['clientes'] for c in resto),
            'ciudades_incluidas': [c['ciudad'] for c in resto],
        }
        resultado['ciudades_agrupadas'] = principales + [otras]

    return resultado


def recuperadores(df, fecha_corte):
    df = anotar_estado_y_mora(df, fecha_corte)
    if df.empty:
        return []

    filas = []
    for recuperador, grupo in df.groupby('recuperador'):
        saldo_total = float(grupo['saldo'].sum())
        saldo_vencido = float(grupo.loc[grupo['estado_calculado'] == 'VENCIDA', 'saldo'].sum())
        saldo_no_vencido = float(grupo.loc[grupo['estado_calculado'] == 'NO VENCIDA', 'saldo'].sum())
        sin_gestion = grupo.loc[grupo['causal'] == SIN_GESTION, 'numero_documento'].nunique()
        filas.append({
            'recuperador': recuperador,
            'saldo_total': round(saldo_total, 2),
            'saldo_vencido': round(saldo_vencido, 2),
            'saldo_no_vencido': round(saldo_no_vencido, 2),
            'porcentaje_vencido': round((saldo_vencido / saldo_total * 100) if saldo_total else 0.0, 2),
            'clientes': int(grupo['identificador_cliente'].nunique()),
            'documentos': int(grupo['numero_documento'].nunique()),
            'documentos_sin_gestion': int(sin_gestion),
        })

    filas.sort(key=lambda f: f['saldo_total'], reverse=True)
    for i, fila in enumerate(filas):
        fila['es_mayor_saldo_pendiente'] = (i == 0)
    return filas


def causales(df, agrupar_otras=False):
    if df.empty:
        return {'causales': [], 'saldo_total': 0.0, 'documentos_total': 0}

    saldo_total = float(df['saldo'].sum())
    documentos_total = int(df['numero_documento'].nunique())

    grupos = df.groupby('causal').agg(
        saldo=('saldo', 'sum'),
        documentos=('numero_documento', 'nunique'),
    ).reset_index()
    grupos['saldo'] = grupos['saldo'].astype(float)
    grupos = grupos.sort_values('saldo', ascending=False).reset_index(drop=True)

    detalle = [
        {
            'causal': row.causal,
            'saldo': round(row.saldo, 2),
            'porcentaje_monetario': round((row.saldo / saldo_total * 100) if saldo_total else 0.0, 2),
            'documentos': int(row.documentos),
            'porcentaje_documentos': round((row.documentos / documentos_total * 100) if documentos_total else 0.0, 2),
        }
        for row in grupos.itertuples()
    ]

    resultado = {'causales': detalle, 'saldo_total': round(saldo_total, 2), 'documentos_total': documentos_total}

    if agrupar_otras and len(detalle) > TOP_CAUSALES_VISIBLES:
        principales = detalle[:TOP_CAUSALES_VISIBLES]
        resto = detalle[TOP_CAUSALES_VISIBLES:]
        otras = {
            'causal': 'OTRAS',
            'saldo': round(sum(c['saldo'] for c in resto), 2),
            'porcentaje_monetario': round(sum(c['porcentaje_monetario'] for c in resto), 2),
            'documentos': sum(c['documentos'] for c in resto),
            'porcentaje_documentos': round(sum(c['porcentaje_documentos'] for c in resto), 2),
            'causales_incluidas': [c['causal'] for c in resto],
        }
        resultado['causales_agrupadas'] = principales + [otras]
        resultado['causales_detalle_completo'] = detalle

    return resultado


def recuperador_causal(df, metrica='saldo'):
    """metrica: 'saldo' | 'documentos' | 'clientes'."""
    if df.empty:
        return {'chart': [], 'matriz': {'filas': [], 'columnas': [], 'celdas': {}, 'totales_fila': {}, 'totales_columna': {}, 'total_general': 0}}

    base = df.groupby(['recuperador', 'causal']).agg(
        saldo=('saldo', 'sum'),
        documentos=('numero_documento', 'nunique'),
        clientes=('identificador_cliente', 'nunique'),
    ).reset_index()
    base['saldo'] = base['saldo'].astype(float)

    columna_valor = {'saldo': 'saldo', 'documentos': 'documentos', 'clientes': 'clientes'}.get(metrica, 'saldo')

    # Los porcentajes del tooltip reflejan la métrica seleccionada (saldo, documentos o
    # clientes), no siempre el saldo monetario.
    total_general_metrica = float(base[columna_valor].sum())
    totales_recuperador_metrica = base.groupby('recuperador')[columna_valor].sum().to_dict()

    chart = []
    for row in base.itertuples():
        valor_metrica = getattr(row, columna_valor)
        total_recuperador_metrica = totales_recuperador_metrica.get(row.recuperador, 0)
        chart.append({
            'recuperador': row.recuperador,
            'causal': row.causal,
            'saldo': round(row.saldo, 2),
            'documentos': int(row.documentos),
            'clientes': int(row.clientes),
            'porcentaje_dentro_recuperador': round((valor_metrica / total_recuperador_metrica * 100) if total_recuperador_metrica else 0.0, 2),
            'porcentaje_sobre_total': round((valor_metrica / total_general_metrica * 100) if total_general_metrica else 0.0, 2),
        })

    recuperadores_unicos = sorted(base['recuperador'].unique().tolist())
    causales_unicas = sorted(base['causal'].unique().tolist())

    celdas = {}
    totales_fila = {}
    totales_columna = {c: 0 for c in causales_unicas}
    total_general = 0
    gestionado_por_fila = {}
    total_por_fila = {}

    for row in base.itertuples():
        valor = getattr(row, columna_valor)
        celdas.setdefault(row.recuperador, {})[row.causal] = valor
        totales_fila[row.recuperador] = totales_fila.get(row.recuperador, 0) + valor
        totales_columna[row.causal] = totales_columna.get(row.causal, 0) + valor
        total_general += valor
        total_por_fila[row.recuperador] = total_por_fila.get(row.recuperador, 0) + valor
        if row.causal != SIN_GESTION:
            gestionado_por_fila[row.recuperador] = gestionado_por_fila.get(row.recuperador, 0) + valor

    porcentajes_gestion = {}
    for recuperador in recuperadores_unicos:
        total = total_por_fila.get(recuperador, 0)
        gestionado = gestionado_por_fila.get(recuperador, 0)
        pct_gestionado = (gestionado / total * 100) if total else 0.0
        porcentajes_gestion[recuperador] = {
            'porcentaje_gestionado': round(pct_gestionado, 2),
            'porcentaje_sin_gestion': round(100 - pct_gestionado, 2) if total else 0.0,
        }

    matriz = {
        'filas': recuperadores_unicos,
        'columnas': causales_unicas,
        'celdas': celdas,
        'totales_fila': {k: (round(v, 2) if metrica == 'saldo' else v) for k, v in totales_fila.items()},
        'totales_columna': {k: (round(v, 2) if metrica == 'saldo' else v) for k, v in totales_columna.items()},
        'total_general': round(total_general, 2) if metrica == 'saldo' else total_general,
        'porcentajes_gestion': porcentajes_gestion,
    }

    return {'chart': chart, 'matriz': matriz}
