import datetime as dt

import pandas as pd
from django.test import SimpleTestCase

from cartera.services.calculator import anotar_estado_y_mora, resumen_kpis
from cartera.utils.dates import calcular_dias_vencidos, calcular_rango_mora, fecha_corte_por_defecto


class FechaCorteTests(SimpleTestCase):
    def test_ultimo_dia_del_mes_anterior(self):
        self.assertEqual(fecha_corte_por_defecto(dt.date(2026, 7, 29)), dt.date(2026, 6, 30))
        self.assertEqual(fecha_corte_por_defecto(dt.date(2026, 1, 15)), dt.date(2025, 12, 31))
        self.assertEqual(fecha_corte_por_defecto(dt.date(2024, 3, 1)), dt.date(2024, 2, 29))  # bisiesto


class RangoMoraTests(SimpleTestCase):
    def setUp(self):
        self.corte = dt.date(2026, 6, 30)

    def test_por_vencer(self):
        self.assertEqual(calcular_rango_mora(dt.date(2026, 7, 1), self.corte), 'POR VENCER')

    def test_rango_0_30(self):
        self.assertEqual(calcular_rango_mora(dt.date(2026, 6, 15), self.corte), '0-30 DÍAS')

    def test_rango_mayor_360(self):
        self.assertEqual(calcular_rango_mora(dt.date(2025, 1, 1), self.corte), 'MÁS DE 360 DÍAS')

    def test_sin_fecha(self):
        self.assertEqual(calcular_rango_mora(None, self.corte), 'SIN FECHA')

    def test_dias_vencidos(self):
        self.assertEqual(calcular_dias_vencidos(dt.date(2026, 2, 1), self.corte), 149)


def _df_ejemplo():
    corte = dt.date(2026, 6, 30)
    filas = [
        # saldo>0, vencida
        {'saldo': 500.0, 'fecha_vencimiento': dt.date(2026, 6, 1), 'identificador_cliente': 'A', 'numero_documento': 'D1'},
        # saldo>0, no vencida
        {'saldo': 300.0, 'fecha_vencimiento': dt.date(2026, 8, 1), 'identificador_cliente': 'A', 'numero_documento': 'D2'},
        # saldo>0, mayor a 120 y 360
        {'saldo': 2500.0, 'fecha_vencimiento': dt.date(2025, 5, 1), 'identificador_cliente': 'B', 'numero_documento': 'D3'},
        # sin fecha
        {'saldo': 150.75, 'fecha_vencimiento': pd.NaT, 'identificador_cliente': 'C', 'numero_documento': 'D4'},
        # saldo cero
        {'saldo': 0.0, 'fecha_vencimiento': dt.date(2026, 5, 1), 'identificador_cliente': 'D', 'numero_documento': 'D5'},
        # saldo negativo
        {'saldo': -50.0, 'fecha_vencimiento': dt.date(2026, 5, 1), 'identificador_cliente': 'E', 'numero_documento': 'D6'},
    ]
    return pd.DataFrame(filas), corte


class AnotarEstadoYMoraTests(SimpleTestCase):
    def test_clasificacion_por_fila(self):
        df, corte = _df_ejemplo()
        anotado = anotar_estado_y_mora(df, corte)
        estados = dict(zip(anotado['numero_documento'], anotado['estado_calculado']))
        self.assertEqual(estados['D1'], 'VENCIDA')
        self.assertEqual(estados['D2'], 'NO VENCIDA')
        self.assertEqual(estados['D3'], 'VENCIDA')
        self.assertEqual(estados['D4'], 'SIN FECHA DE VENCIMIENTO')
        self.assertEqual(estados['D5'], 'SALDO CERO')
        self.assertEqual(estados['D6'], 'SALDO A FAVOR')


class ResumenKpisTests(SimpleTestCase):
    def test_totales_y_porcentajes(self):
        df, corte = _df_ejemplo()
        resumen = resumen_kpis(df, corte)

        self.assertEqual(resumen['total_clientes'], 5)
        self.assertEqual(resumen['total_documentos'], 6)
        self.assertAlmostEqual(resumen['cartera_total'], 3450.75, places=2)
        self.assertAlmostEqual(resumen['cartera_vencida']['valor'], 3000.0, places=2)
        self.assertAlmostEqual(resumen['cartera_no_vencida']['valor'], 300.0, places=2)
        self.assertAlmostEqual(resumen['sin_fecha_vencimiento']['valor'], 150.75, places=2)
        self.assertAlmostEqual(resumen['mayor_120_dias']['valor'], 2500.0, places=2)
        self.assertAlmostEqual(resumen['mayor_360_dias']['valor'], 2500.0, places=2)
        self.assertEqual(resumen['mayor_360_dias']['clientes'], 1)

        suma_porcentajes = (
            resumen['cartera_vencida']['porcentaje']
            + resumen['cartera_no_vencida']['porcentaje']
            + resumen['sin_fecha_vencimiento']['porcentaje']
        )
        self.assertAlmostEqual(suma_porcentajes, 100.0, places=1)
