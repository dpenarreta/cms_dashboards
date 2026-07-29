"""Clasificación de cartera y cálculo de KPIs (secciones 7, 8, 9 y 11 de la especificación).

Todo se calcula dinámicamente a partir de `fecha_corte`, que el usuario puede modificar en
cualquier momento sin volver a procesar el archivo.
"""

import numpy as np
import pandas as pd

from ..utils.dates import calcular_rango_mora

DIAS_120 = 120
DIAS_360 = 360


def _dias_vencidos(fecha_vencimiento, fecha_corte):
    if pd.isna(fecha_vencimiento):
        return np.nan
    return (fecha_corte - fecha_vencimiento).days


def anotar_estado_y_mora(df, fecha_corte):
    """Agrega columnas calculadas: dias_vencidos, estado_calculado, rango_mora."""
    df = df.copy()
    if df.empty:
        df['dias_vencidos'] = pd.Series(dtype='float64')
        df['estado_calculado'] = pd.Series(dtype='object')
        df['rango_mora'] = pd.Series(dtype='object')
        return df

    df['dias_vencidos'] = df['fecha_vencimiento'].apply(lambda f: _dias_vencidos(f, fecha_corte))

    def estado(row):
        saldo = row['saldo']
        if saldo == 0:
            return 'SALDO CERO'
        if saldo < 0:
            return 'SALDO A FAVOR'
        if pd.isna(row['fecha_vencimiento']):
            return 'SIN FECHA DE VENCIMIENTO'
        if row['fecha_vencimiento'] <= fecha_corte:
            return 'VENCIDA'
        return 'NO VENCIDA'

    df['estado_calculado'] = df.apply(estado, axis=1)
    df['rango_mora'] = df['fecha_vencimiento'].apply(lambda f: calcular_rango_mora(f, fecha_corte))
    return df


def resumen_kpis(df, fecha_corte):
    df = anotar_estado_y_mora(df, fecha_corte)

    total_clientes = df['identificador_cliente'].nunique()
    total_documentos = df['numero_documento'].nunique()

    con_saldo_positivo = df[df['saldo'] > 0]
    cartera_total = float(con_saldo_positivo['saldo'].sum()) if not con_saldo_positivo.empty else 0.0

    def bloque(mask):
        subset = con_saldo_positivo[mask]
        valor = float(subset['saldo'].sum()) if not subset.empty else 0.0
        porcentaje = (valor / cartera_total * 100) if cartera_total else 0.0
        return valor, porcentaje, subset

    valor_vencida, pct_vencida, subset_vencida = bloque(con_saldo_positivo['estado_calculado'] == 'VENCIDA')
    valor_no_vencida, pct_no_vencida, _ = bloque(con_saldo_positivo['estado_calculado'] == 'NO VENCIDA')
    valor_sin_fecha, pct_sin_fecha, subset_sin_fecha = bloque(con_saldo_positivo['estado_calculado'] == 'SIN FECHA DE VENCIMIENTO')

    mask_120 = (con_saldo_positivo['dias_vencidos'] > DIAS_120)
    mask_360 = (con_saldo_positivo['dias_vencidos'] > DIAS_360)
    valor_120, pct_120, subset_120 = bloque(mask_120)
    valor_360, pct_360, subset_360 = bloque(mask_360)

    saldo_promedio_cliente = (cartera_total / total_clientes) if total_clientes else 0.0

    return {
        'fecha_corte': fecha_corte.isoformat(),
        'total_clientes': int(total_clientes),
        'total_documentos': int(total_documentos),
        'saldo_promedio_por_cliente': round(saldo_promedio_cliente, 2),
        'cartera_total': round(cartera_total, 2),
        'cartera_vencida': {'valor': round(valor_vencida, 2), 'porcentaje': round(pct_vencida, 2)},
        'cartera_no_vencida': {'valor': round(valor_no_vencida, 2), 'porcentaje': round(pct_no_vencida, 2)},
        'sin_fecha_vencimiento': {
            'valor': round(valor_sin_fecha, 2),
            'porcentaje': round(pct_sin_fecha, 2),
            'documentos': int(subset_sin_fecha['numero_documento'].nunique()) if not subset_sin_fecha.empty else 0,
        },
        'mayor_120_dias': {
            'valor': round(valor_120, 2),
            'porcentaje': round(pct_120, 2),
            'clientes': int(subset_120['identificador_cliente'].nunique()) if not subset_120.empty else 0,
            'documentos': int(subset_120['numero_documento'].nunique()) if not subset_120.empty else 0,
        },
        'mayor_360_dias': {
            'valor': round(valor_360, 2),
            'porcentaje': round(pct_360, 2),
            'clientes': int(subset_360['identificador_cliente'].nunique()) if not subset_360.empty else 0,
            'documentos': int(subset_360['numero_documento'].nunique()) if not subset_360.empty else 0,
        },
    }
