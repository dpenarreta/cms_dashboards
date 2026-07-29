import datetime as dt

import pandas as pd
from django.test import SimpleTestCase

from cartera.services import aggregations


def _df_top_clientes():
    corte = dt.date(2026, 6, 30)
    filas = [
        {'saldo': 500.0, 'fecha_vencimiento': dt.date(2026, 6, 1), 'identificador_cliente': 'RUC:1', 'numero_documento': 'D1', 'cliente': 'ACME', 'ruc_cliente': '1'},
        {'saldo': 300.0, 'fecha_vencimiento': dt.date(2026, 8, 1), 'identificador_cliente': 'RUC:1', 'numero_documento': 'D2', 'cliente': 'ACME', 'ruc_cliente': '1'},
        {'saldo': 100.0, 'fecha_vencimiento': dt.date(2026, 9, 1), 'identificador_cliente': 'RUC:1', 'numero_documento': 'D3', 'cliente': 'ACME S.A.', 'ruc_cliente': '1'},
        {'saldo': 200.0, 'fecha_vencimiento': dt.date(2026, 5, 1), 'identificador_cliente': 'RUC:2', 'numero_documento': 'D4', 'cliente': 'BETA', 'ruc_cliente': '2'},
    ]
    return pd.DataFrame(filas), corte


class TopClientesTests(SimpleTestCase):
    def test_agrupa_por_identificador_y_calcula_vencido_no_vencido(self):
        df, corte = _df_top_clientes()
        resultado = aggregations.top_clientes(df, corte, cartera_total=1100.0, top_n=10)
        acme = next(r for r in resultado if r['identificador_cliente'] == 'RUC:1')
        self.assertEqual(acme['documentos'], 3)
        self.assertAlmostEqual(acme['saldo_total'], 900.0, places=2)
        self.assertAlmostEqual(acme['saldo_vencido'], 500.0, places=2)
        self.assertAlmostEqual(acme['saldo_no_vencido'], 400.0, places=2)

    def test_orden_descendente(self):
        df, corte = _df_top_clientes()
        resultado = aggregations.top_clientes(df, corte, cartera_total=1100.0, top_n=10)
        saldos = [r['saldo_total'] for r in resultado]
        self.assertEqual(saldos, sorted(saldos, reverse=True))


class ParetoCiudadesTests(SimpleTestCase):
    def test_porcentaje_acumulado_llega_a_100(self):
        corte = dt.date(2026, 6, 30)
        filas = [
            {'saldo': 4000.0, 'fecha_vencimiento': dt.date(2026, 6, 1), 'identificador_cliente': 'A', 'numero_documento': 'D1', 'ciudad': 'GUAYAQUIL'},
            {'saldo': 2900.5, 'fecha_vencimiento': dt.date(2026, 6, 1), 'identificador_cliente': 'B', 'numero_documento': 'D2', 'ciudad': 'QUITO'},
        ]
        df = pd.DataFrame(filas)
        resultado = aggregations.pareto_ciudades(df, corte)
        ciudades = resultado['ciudades']
        self.assertEqual(ciudades[0]['ciudad'], 'GUAYAQUIL')
        self.assertAlmostEqual(ciudades[0]['porcentaje_acumulado'], 57.97, places=1)
        self.assertAlmostEqual(ciudades[-1]['porcentaje_acumulado'], 100.0, places=1)
        self.assertAlmostEqual(resultado['total_vencida'], 6900.5, places=1)

    def test_agrupa_otras_ciudades_cuando_hay_mas_de_8(self):
        corte = dt.date(2026, 6, 30)
        filas = [
            {'saldo': float(100 - i), 'fecha_vencimiento': dt.date(2026, 6, 1), 'identificador_cliente': f'C{i}',
             'numero_documento': f'D{i}', 'ciudad': f'CIUDAD_{i}'}
            for i in range(10)
        ]
        df = pd.DataFrame(filas)
        resultado = aggregations.pareto_ciudades(df, corte, agrupar_otras=True)
        self.assertIn('ciudades_agrupadas', resultado)
        agrupadas = resultado['ciudades_agrupadas']
        self.assertEqual(len(agrupadas), 9)  # 8 principales + OTRAS CIUDADES
        otras = agrupadas[-1]
        self.assertEqual(otras['ciudad'], 'OTRAS CIUDADES')
        self.assertEqual(len(otras['ciudades_incluidas']), 2)


class CausalesTests(SimpleTestCase):
    def test_agrupa_y_calcula_porcentajes(self):
        filas = [
            {'saldo': 100.0, 'numero_documento': 'D1', 'causal': 'GESTIONANDO'},
            {'saldo': 200.0, 'numero_documento': 'D2', 'causal': 'GESTIONANDO'},
            {'saldo': 50.0, 'numero_documento': 'D3', 'causal': 'SIN GESTIÓN'},
        ]
        df = pd.DataFrame(filas)
        resultado = aggregations.causales(df)
        gestionando = next(c for c in resultado['causales'] if c['causal'] == 'GESTIONANDO')
        self.assertAlmostEqual(gestionando['saldo'], 300.0, places=2)
        self.assertAlmostEqual(gestionando['porcentaje_monetario'], 300 / 350 * 100, places=1)

    def test_agrupa_otras_cuando_hay_mas_de_8(self):
        filas = [{'saldo': float(i + 1), 'numero_documento': f'D{i}', 'causal': f'CAUSAL_{i}'} for i in range(10)]
        df = pd.DataFrame(filas)
        resultado = aggregations.causales(df, agrupar_otras=True)
        self.assertIn('causales_agrupadas', resultado)
        self.assertEqual(len(resultado['causales_agrupadas']), 9)  # 8 principales + OTRAS
        self.assertEqual(resultado['causales_agrupadas'][-1]['causal'], 'OTRAS')


class RecuperadorCausalTests(SimpleTestCase):
    def test_matriz_totales_y_porcentaje_gestionado(self):
        filas = [
            {'saldo': 100.0, 'numero_documento': 'D1', 'identificador_cliente': 'A', 'recuperador': 'R1', 'causal': 'GESTIONANDO'},
            {'saldo': 50.0, 'numero_documento': 'D2', 'identificador_cliente': 'B', 'recuperador': 'R1', 'causal': 'SIN GESTIÓN'},
            {'saldo': 200.0, 'numero_documento': 'D3', 'identificador_cliente': 'C', 'recuperador': 'R2', 'causal': 'GESTIONANDO'},
        ]
        df = pd.DataFrame(filas)
        resultado = aggregations.recuperador_causal(df, metrica='saldo')
        matriz = resultado['matriz']

        self.assertAlmostEqual(matriz['totales_fila']['R1'], 150.0, places=2)
        self.assertAlmostEqual(matriz['total_general'], 350.0, places=2)
        # R1: 100 gestionado de 150 total -> 66.67%
        self.assertAlmostEqual(matriz['porcentajes_gestion']['R1']['porcentaje_gestionado'], 66.67, places=1)
        # R2: 100% gestionado
        self.assertAlmostEqual(matriz['porcentajes_gestion']['R2']['porcentaje_gestionado'], 100.0, places=1)

    def test_porcentajes_del_chart_siguen_la_metrica_seleccionada(self):
        filas = [
            {'saldo': 100.0, 'numero_documento': 'D1', 'identificador_cliente': 'A', 'recuperador': 'R1', 'causal': 'GESTIONANDO'},
            {'saldo': 100.0, 'numero_documento': 'D2', 'identificador_cliente': 'B', 'recuperador': 'R1', 'causal': 'SIN GESTIÓN'},
        ]
        df = pd.DataFrame(filas)
        resultado = aggregations.recuperador_causal(df, metrica='documentos')
        fila_gestionando = next(f for f in resultado['chart'] if f['causal'] == 'GESTIONANDO')
        # Con metrica=documentos, cada causal tiene 1 documento de 2 totales -> 50%, no 100% ni el % de saldo.
        self.assertAlmostEqual(fila_gestionando['porcentaje_dentro_recuperador'], 50.0, places=1)
