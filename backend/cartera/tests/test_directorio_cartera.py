"""Dashboard Directorio — réplica de la pestaña "6. Cartera" de un informe financiero.

Lo que estas pruebas protegen es que el dashboard sea PARAMETRIZABLE. Una versión anterior guardaba
el contenido con una forma propia y `mapeo` vacío: se veía igual, pero las columnas, las metas y el
Top-N estaban quemados en el código y "Configurar componente → Datos" no tenía nada que editar.

Por eso acá se verifica, además de la estructura y la coherencia de las cifras, que cada sección
guarde un `mapeo` completo y que su contenido sea el GENÉRICO — el mismo que produce
`calcular_contenido_por_calculo` para cualquier dashboard. Esa es la condición para que la pantalla
de configuración de siempre pueda recalcularlas.
"""

from datetime import date

import pandas as pd
from django.test import TestCase

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


def _contenidos(**parametros):
    return {spec['component_id']: contenido
            for spec, contenido in directorio_cartera.calcular_contenidos(_df(), CORTE, **parametros)}


class ParametrizacionTests(TestCase):
    """El motivo de ser de este archivo: que nada quede quemado."""

    def test_cada_seccion_guarda_un_mapeo_completo(self):
        for spec in directorio_cartera.especificacion():
            with self.subTest(seccion=spec['component_id']):
                mapeo = spec['mapeo']
                self.assertTrue(mapeo.get('disponible'))
                self.assertEqual(mapeo['calculo'], spec['calculo'])
                # Sin columnas en el mapeo no hay nada que ofrecer en "Configurar componente".
                self.assertTrue(
                    any(clave.startswith('columna_') for clave in mapeo),
                    f'{spec["component_id"]} no declara ninguna columna en su mapeo',
                )

    def test_los_calculos_son_los_que_la_interfaz_sabe_editar(self):
        # `SlotFields.jsx` tiene un formulario por cada uno de estos. Un cálculo fuera de esta lista
        # se vería, pero no se podría reconfigurar desde la pantalla.
        editables = {'kpi', 'tramos_antiguedad', 'cumplimiento_metas', 'concentracion',
                     'antiguedad_por_deudor'}
        for spec in directorio_cartera.especificacion():
            with self.subTest(seccion=spec['component_id']):
                self.assertIn(spec['calculo'], editables)

    def test_las_columnas_son_parametros_y_llegan_al_mapeo(self):
        specs = directorio_cartera.especificacion(
            columna_valor='Importe', columna_fecha='Vence', columna_cliente='Razón social',
        )
        mapeos = {s['component_id']: s['mapeo'] for s in specs}
        self.assertEqual(mapeos['cartera-total']['columna_valor'], 'Importe')
        self.assertEqual(mapeos['antiguedad-de-cartera']['columna_fecha'], 'Vence')
        self.assertEqual(mapeos['concentracion-de-cartera']['columna_id'], 'Razón social')
        self.assertEqual(mapeos['al-corriente']['columna_filtro'], 'Vence')

    def test_la_cantidad_de_deudores_es_un_parametro(self):
        specs = {s['component_id']: s for s in directorio_cartera.especificacion(deudores=4)}
        self.assertEqual(specs['mayores-deudores']['mapeo']['cuantos'], 4)

    def test_cambiar_la_cantidad_de_deudores_cambia_el_resultado(self):
        self.assertEqual(len(_contenidos(deudores=1)['mayores-deudores']['deudores']), 1)
        self.assertEqual(len(_contenidos(deudores=3)['mayores-deudores']['deudores']), 3)

    def test_el_top_n_es_un_parametro(self):
        specs = {s['component_id']: s for s in directorio_cartera.especificacion(top_n=3)}
        self.assertEqual(specs['concentracion-de-cartera']['mapeo']['top_n'], 3)

    def test_el_titulo_de_concentracion_no_lleva_el_numero_escrito(self):
        # El número va como marcador `{n}` y lo resuelve el renderer con el `top_n` vigente. Si se
        # escribiera acá, cambiar el Top-N desde la interfaz actualizaría las tarjetas y la tabla
        # pero dejaría el título con la cifra vieja — el título se guarda una sola vez.
        titulo = next(s['titulo'] for s in directorio_cartera.especificacion(top_n=3)
                      if s['component_id'] == 'concentracion-de-cartera')
        self.assertIn('{n}', titulo)
        self.assertNotIn('TOP 3', titulo)

    def test_cambiar_el_top_n_cambia_el_resultado(self):
        con_2 = _contenidos(top_n=2)['concentracion-de-cartera']
        con_3 = _contenidos(top_n=3)['concentracion-de-cartera']
        # N principales + la fila "Resto".
        self.assertEqual(len(con_2['filas']), 3)
        self.assertEqual(len(con_3['filas']), 4)

    def test_las_metas_viajan_en_el_mapeo_y_no_en_el_codigo_del_renderer(self):
        spec = next(s for s in directorio_cartera.especificacion()
                    if s['component_id'] == 'cumplimiento-metas-antiguedad')
        metas = spec['mapeo']['metas']
        self.assertEqual(len(metas), 6)
        self.assertEqual(metas[0]['meta_min'], 50)
        self.assertEqual(metas[-1]['meta_max'], 5)

    def test_el_contenido_es_el_generico_no_una_forma_propia(self):
        # Si el contenido tuviera una forma propia, la primera edición desde la interfaz —que
        # recalcula con `calcular_contenido_por_calculo`— dejaría la sección en blanco.
        for component_id, contenido in _contenidos().items():
            with self.subTest(seccion=component_id):
                self.assertIsNotNone(contenido)
                self.assertNotIn('bloque', contenido)
                self.assertIn('titulo', contenido)
                esperado = plantilla.calcular_contenido_por_calculo(
                    _df(),
                    next(s['calculo'] for s in directorio_cartera.especificacion()
                         if s['component_id'] == component_id),
                    contenido['titulo'],
                    next(s['mapeo'] for s in directorio_cartera.especificacion()
                         if s['component_id'] == component_id),
                    fecha_referencia=CORTE,
                )
                self.assertEqual(contenido, esperado)


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
            'antiguedad-de-cartera', 'cumplimiento-metas-antiguedad', 'concentracion-de-cartera',
            'mayores-deudores',
        ])

    def test_oculta_las_posiciones_de_fabrica(self):
        fabrica = self.layout.components.filter(component_id__in=directorio_cartera.IDS_FABRICA)
        self.assertEqual(fabrica.count(), 13)
        self.assertFalse(fabrica.filter(is_visible=True).exists())

    def test_las_secciones_no_quedan_bloqueadas(self):
        # El dashboard es del usuario: tiene que poder mover, redimensionar y reconfigurar cada
        # sección. Bloquearlas era justamente parte del problema de "está quemado".
        for componente in self.layout.components.filter(is_visible=True):
            with self.subTest(seccion=componente.component_id):
                self.assertFalse(componente.config.get('bloqueado'))
                self.assertEqual(componente.config.get('render'), 'directorio')
                self.assertIn(componente.config.get('bloque'),
                              {'kpi', 'antiguedad', 'cumplimiento', 'concentracion', 'deudores'})

    def test_el_mapeo_queda_persistido_en_cada_componente(self):
        for componente in self.layout.components.filter(is_visible=True):
            with self.subTest(seccion=componente.component_id):
                self.assertTrue(componente.mapeo, 'sin mapeo no hay nada que configurar')
                self.assertIn('calculo', componente.mapeo)

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
        self.assertEqual(concentracion['total'][1], total)
        self.assertAlmostEqual(sum(fila[1] for fila in concentracion['filas']), total, places=2)

    def test_el_acumulado_de_cumplimiento_mas_la_cola_dan_cien(self):
        filas = self.contenidos['cumplimiento-metas-antiguedad']['filas']
        self.assertAlmostEqual(filas[4][2] + filas[5][2], 100.0, places=1)

    def test_el_cumplimiento_evalua_las_metas_y_ninguna_queda_sin_meta(self):
        for fila in self.contenidos['cumplimiento-metas-antiguedad']['filas']:
            with self.subTest(tramo=fila[0]):
                self.assertNotEqual(fila[3], 'Sin meta')


class ColumnasTests(TestCase):
    def test_detecta_las_columnas_que_faltan(self):
        df = pd.DataFrame({'Cliente': ['x'], 'Saldo': [1.0]})
        self.assertEqual(directorio_cartera.columnas_faltantes(df), ['Fecha de Vencimiento'])

    def test_las_columnas_requeridas_siguen_a_los_parametros(self):
        faltantes = directorio_cartera.columnas_faltantes(_df(), columna_valor='Importe')
        self.assertEqual(faltantes, ['Importe'])
