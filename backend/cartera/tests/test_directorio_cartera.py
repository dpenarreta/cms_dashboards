"""Estructura fija del Dashboard Directorio.

Este dashboard es la excepción declarada del proyecto (no usa las 13 posiciones de la plantilla),
así que lo que hay que proteger es justamente eso: que su estructura no se degrade silenciosamente
a la genérica, y que las posiciones de fábrica queden ocultas en vez de convivir con datos reales.
"""

from datetime import date

import pandas as pd
from django.test import TestCase

from cartera.models import DashboardComponent
from cartera.services import dashboard_layout, directorio_cartera, plantilla

DASHBOARD = 'directorio-prueba'
CORTE = date(2026, 8, 31)


def _df():
    """Cuatro facturas con vencimientos elegidos alrededor de la fecha de corte: una por vencer,
    una vencida hace poco y dos vencidas hace más de 120 días."""
    return pd.DataFrame({
        'Cliente': ['ACME', 'ACME', 'BETA', 'GAMMA'],
        'Saldo': [1000.0, 500.0, 300.0, 200.0],
        'Fecha de Vencimiento': [
            date(2026, 9, 30),   # todavía no vence al 31/08
            date(2026, 8, 20),   # vencida hace 11 días
            date(2026, 1, 15),   # vencida hace más de 120 días
            date(2026, 2, 10),   # vencida hace más de 120 días
        ],
    })


class EstructuraTests(TestCase):
    def setUp(self):
        plantilla.sembrar_plantilla(DASHBOARD)
        directorio_cartera.construir(DASHBOARD, _df(), fecha_referencia=CORTE)
        self.layout = dashboard_layout.obtener_o_crear_layout(DASHBOARD)

    def _componente(self, component_id):
        return DashboardComponent.objects.get(layout=self.layout, component_id=component_id)

    def test_crea_los_siete_componentes_del_diseno(self):
        esperados = [spec['component_id'] for spec in directorio_cartera.especificacion()]
        self.assertEqual(len(esperados), 7)
        visibles = list(
            self.layout.components.filter(is_visible=True).order_by('order').values_list('component_id', flat=True)
        )
        self.assertEqual(visibles, esperados)

    def test_oculta_y_bloquea_las_posiciones_de_fabrica(self):
        # Conviven en la base pero no en pantalla: sin esto un usuario podría "Mostrar" un KPI
        # ficticio genérico junto a las cifras reales de cartera.
        fabrica = self.layout.components.filter(component_id__in=directorio_cartera.IDS_FABRICA)
        self.assertEqual(fabrica.count(), 13)
        for componente in fabrica:
            with self.subTest(componente=componente.component_id):
                self.assertFalse(componente.is_visible)
                self.assertTrue(componente.config.get('bloqueado'))

    def test_los_componentes_propios_quedan_bloqueados(self):
        for spec in directorio_cartera.especificacion():
            with self.subTest(componente=spec['component_id']):
                config = self._componente(spec['component_id']).config
                self.assertTrue(config.get('bloqueado'))
                self.assertEqual(config.get('zona'), 'personal')


class ContenidoTests(TestCase):
    def setUp(self):
        plantilla.sembrar_plantilla(DASHBOARD)
        directorio_cartera.construir(DASHBOARD, _df(), fecha_referencia=CORTE)
        self.layout = dashboard_layout.obtener_o_crear_layout(DASHBOARD)

    def _contenido(self, component_id):
        return DashboardComponent.objects.get(layout=self.layout, component_id=component_id).content

    def test_los_kpis_reparten_el_total_segun_su_filtro(self):
        total = self._contenido('cartera-total')['valor']
        corriente = self._contenido('al-corriente')['valor']
        vencida = self._contenido('vencida-total')['valor']
        mas_120 = self._contenido('vencida-mas-120-dias')['valor']

        self.assertEqual(total, 2000.0)
        self.assertEqual(corriente, 1000.0)   # solo la que aún no vence
        self.assertEqual(vencida, 1000.0)     # las otras tres
        self.assertEqual(mas_120, 500.0)      # las dos más viejas
        # Con todas las fechas legibles, corriente + vencida tiene que dar el total. Si algún día
        # esto falla con datos reales, son filas sin fecha parseable: no entran en ningún tramo.
        self.assertEqual(corriente + vencida, total)

    def test_el_grafico_de_antiguedad_trae_los_seis_tramos_con_su_color(self):
        componente = DashboardComponent.objects.get(layout=self.layout, component_id='antiguedad-de-cartera')
        self.assertEqual(componente.content['categorias'], directorio_cartera.TRAMOS)
        colores = componente.styles['coloresPorCategoria']
        self.assertEqual([colores[t] for t in directorio_cartera.TRAMOS], directorio_cartera.COLORES_TRAMOS)

    def test_la_tabla_de_cumplimiento_evalua_las_metas(self):
        contenido = self._contenido('cumplimiento-metas-antiguedad')
        self.assertEqual(contenido['columnas'], ['Tramo', 'Saldo', '% acumulado', 'Resultado'])
        self.assertEqual(len(contenido['filas']), 6)
        # Con metas configuradas ninguna fila puede quedar en "Sin meta": si apareciera, es que el
        # mapeo perdió `metas` y las insignias del diseño dejarían de tener sentido.
        resultados = [fila[3] for fila in contenido['filas']]
        self.assertNotIn('Sin meta', resultados)

    def test_la_tabla_de_concentracion_cierra_en_el_total(self):
        contenido = self._contenido('concentracion-de-cartera')
        self.assertEqual(contenido['columnas'], ['Cliente', 'Saldo', '% del total', '% acumulado'])
        self.assertEqual(contenido['total'], ['Total', 2000.0, 100.0, 100.0])

    def test_reconstruir_no_duplica_componentes(self):
        directorio_cartera.construir(DASHBOARD, _df(), fecha_referencia=CORTE)
        ids = list(self.layout.components.values_list('component_id', flat=True))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 20)  # 7 propios + 13 de fábrica


class ColumnasTests(TestCase):
    def test_detecta_las_columnas_que_faltan(self):
        df = pd.DataFrame({'Cliente': ['x'], 'Saldo': [1.0]})
        self.assertEqual(directorio_cartera.columnas_faltantes(df), ['Fecha de Vencimiento'])

    def test_con_todas_las_columnas_no_falta_ninguna(self):
        self.assertEqual(directorio_cartera.columnas_faltantes(_df()), [])
