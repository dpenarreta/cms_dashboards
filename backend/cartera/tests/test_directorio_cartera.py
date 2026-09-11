"""Dashboard Directorio — réplica de la pestaña "6. Cartera" de un informe financiero.

Lo que hay que proteger acá es doble: que la estructura del informe no se degrade a la genérica
(es la excepción declarada del proyecto) y que los números de cada sección sean CONSISTENTES ENTRE
SÍ. Un informe financiero en el que los KPI no cierran contra la tabla es peor que no tenerlo:
parece correcto y no lo es.
"""

from datetime import date

import pandas as pd
from django.test import TestCase

from cartera.models import DashboardComponent
from cartera.services import dashboard_layout, directorio_cartera, plantilla

DASHBOARD = 'directorio-prueba'
CORTE = date(2026, 8, 31)


def _df():
    """Facturas con vencimientos elegidos alrededor del corte para caer en tramos distintos."""
    return pd.DataFrame({
        'Cliente': ['ACME', 'ACME', 'BETA', 'GAMMA', 'DELTA'],
        'Saldo': [1000.0, 500.0, 300.0, 150.0, 50.0],
        'Fecha de Vencimiento': [
            date(2026, 9, 30),   # aún no vence al 31/08 -> Anticipada
            date(2026, 8, 20),   # vencida hace 11 días  -> 30 días
            date(2026, 1, 15),   # vencida hace >120     -> +120 días
            date(2026, 2, 10),   # vencida hace >120     -> +120 días
            date(2026, 7, 20),   # vencida hace 42 días  -> 60 días
        ],
    })


def _contenidos():
    return {spec['component_id']: contenido
            for spec, contenido in directorio_cartera.construir_contenidos(_df(), CORTE)}


class EstructuraTests(TestCase):
    def setUp(self):
        plantilla.sembrar_plantilla(DASHBOARD)
        directorio_cartera.construir(DASHBOARD, _df(), CORTE)
        self.layout = dashboard_layout.obtener_o_crear_layout(DASHBOARD)

    def test_crea_las_secciones_del_informe_en_orden(self):
        visibles = list(
            self.layout.components.filter(is_visible=True).order_by('order').values_list('component_id', flat=True)
        )
        self.assertEqual(visibles, [
            'cartera-total', 'al-corriente', 'vencida-total', 'vencida-mas-120-dias',
            'antiguedad-de-cartera', 'cumplimiento-metas-antiguedad',
            'concentracion-de-cartera', 'mayores-deudores',
        ])

    def test_oculta_y_bloquea_las_posiciones_de_fabrica(self):
        # Conviven en la base pero no en pantalla: sin esto un usuario podría "Mostrar" un KPI
        # ficticio genérico junto a las cifras del informe.
        fabrica = self.layout.components.filter(component_id__in=directorio_cartera.IDS_FABRICA)
        self.assertEqual(fabrica.count(), 13)
        for componente in fabrica:
            with self.subTest(componente=componente.component_id):
                self.assertFalse(componente.is_visible)
                self.assertTrue(componente.config.get('bloqueado'))

    def test_todas_las_secciones_piden_el_renderer_propio(self):
        # `config.render` es lo que hace que el frontend use los componentes a medida. Si se
        # perdiera, la pantalla volvería a dibujarse con los genéricos y el informe se desarmaría.
        for componente in self.layout.components.filter(is_visible=True):
            with self.subTest(componente=componente.component_id):
                self.assertEqual(componente.config.get('render'), 'directorio')
                self.assertTrue(componente.config.get('bloqueado'))

    def test_reconstruir_no_duplica_componentes(self):
        directorio_cartera.construir(DASHBOARD, _df(), CORTE)
        ids = list(self.layout.components.values_list('component_id', flat=True))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 21)  # 8 secciones + 13 de fábrica


class CoherenciaEntreSeccionesTests(TestCase):
    """Las cifras del informe tienen que cerrar entre sí, no solo ser correctas por separado."""

    def setUp(self):
        self.contenidos = _contenidos()

    def test_los_kpis_reparten_el_total(self):
        total = self.contenidos['cartera-total']['valor']
        corriente = self.contenidos['al-corriente']['valor']
        vencida = self.contenidos['vencida-total']['valor']

        self.assertEqual(total, 2000.0)
        self.assertEqual(corriente, 1000.0)
        self.assertEqual(vencida, 1000.0)
        self.assertEqual(corriente + vencida, total)

    def test_los_tramos_del_grafico_suman_el_total(self):
        total = self.contenidos['cartera-total']['valor']
        self.assertEqual(sum(self.contenidos['antiguedad-de-cartera']['valores']), total)

    def test_el_kpi_de_mas_120_coincide_con_la_cola_del_grafico(self):
        cola = self.contenidos['antiguedad-de-cartera']['valores'][-1]
        self.assertEqual(self.contenidos['vencida-mas-120-dias']['valor'], cola)

    def test_la_concentracion_cierra_en_el_total(self):
        concentracion = self.contenidos['concentracion-de-cartera']
        total = self.contenidos['cartera-total']['valor']
        self.assertEqual(concentracion['fila_total'][1], total)
        suma_clientes = sum(fila[1] for fila in concentracion['filas']) + concentracion['fila_resto'][1]
        self.assertAlmostEqual(suma_clientes, total, places=2)

    def test_el_acumulado_de_cumplimiento_mas_la_cola_dan_cien(self):
        # El invariante real de esta tabla: las 6 filas NO suman 100% entre sí (las 5 primeras se
        # contienen unas a otras), pero el acumulado ≤120 más la cola >120 sí.
        filas = self.contenidos['cumplimiento-metas-antiguedad']['filas']
        self.assertAlmostEqual(filas[4]['porcentaje'] + filas[5]['porcentaje'], 100.0, places=1)


class FormatoDelInformeTests(TestCase):
    def setUp(self):
        self.contenidos = _contenidos()

    def test_cada_barra_trae_su_etiqueta_con_monto_y_porcentaje(self):
        grafico = self.contenidos['antiguedad-de-cartera']
        self.assertEqual(len(grafico['etiquetas']), len(grafico['categorias']))
        self.assertEqual(len(grafico['colores']), len(grafico['categorias']))
        # Formato del informe: `$1000K (50%)`, sin separador de miles en la parte compacta.
        for etiqueta in grafico['etiquetas']:
            with self.subTest(etiqueta=etiqueta):
                self.assertRegex(etiqueta, r'^\$\d+K \(\d+%\)$')

    def test_la_tabla_de_cumplimiento_trae_la_columna_de_meta(self):
        cumplimiento = self.contenidos['cumplimiento-metas-antiguedad']
        self.assertEqual(cumplimiento['columnas'],
                         ['EDAD DE CARTERA', 'META (MÍN./MÁX.)', 'VALOR ACUMULADO', 'RESULTADO'])
        for fila in cumplimiento['filas']:
            with self.subTest(tramo=fila['edad']):
                self.assertRegex(fila['meta'], r'^[≥≤] \d+%$')
                self.assertIn(fila['cumple'], (True, False))

    def test_los_textos_narrativos_conservan_sus_comas(self):
        # Una versión anterior formateaba los números con un `.replace(',', '.')` sobre la frase
        # entera y convertía las comas de la redacción en puntos ("del saldo. con un ticket").
        for clave in ('concentracion-de-cartera', 'mayores-deudores'):
            with self.subTest(seccion=clave):
                textos = [v for k, v in self.contenidos[clave].items()
                          if k in ('hallazgos', 'nota', 'fuente') and v]
                self.assertTrue(textos)
                for texto in textos:
                    self.assertNotRegex(texto, r'[a-záéíóúñ]\. [a-záéíóúñ]')

    def test_la_concentracion_trae_las_dos_tarjetas_resumen(self):
        resumen = self.contenidos['concentracion-de-cartera']['resumen']
        self.assertEqual(len(resumen), 2)
        self.assertTrue(resumen[0]['etiqueta'].startswith('TOP'))
        self.assertTrue(resumen[1]['etiqueta'].startswith('RESTO'))

    def test_los_mayores_deudores_traen_su_desglose_por_tramo(self):
        deudores = self.contenidos['mayores-deudores']['deudores']
        self.assertEqual(len(deudores), 2)
        # ACME es el mayor deudor del archivo de prueba (1000 + 500).
        self.assertEqual(deudores[0]['nombre'], 'ACME')
        self.assertEqual(deudores[0]['saldo'], 1500.0)
        self.assertTrue(deudores[0]['filas'])
        # Solo tramos con saldo: el informe no lista filas en cero.
        for fila in deudores[0]['filas']:
            self.assertGreater(fila['saldo'], 0)


class ColumnasTests(TestCase):
    def test_detecta_las_columnas_que_faltan(self):
        df = pd.DataFrame({'Cliente': ['x'], 'Saldo': [1.0]})
        self.assertEqual(directorio_cartera.columnas_faltantes(df), ['Fecha de Vencimiento'])

    def test_con_todas_las_columnas_no_falta_ninguna(self):
        self.assertEqual(directorio_cartera.columnas_faltantes(_df()), [])
