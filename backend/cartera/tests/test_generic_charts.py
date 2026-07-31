"""Análisis genérico de columnas, recomendación de gráficas y confirmación (una por una) a partir
de un archivo cargado — flujo "cargar archivo → analizar columnas → recomendar gráficas →
agregar", sin depender del esquema fijo de cartera (`services/generic_charts.py`)."""

import os

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from cartera.models import CargaArchivo, Dashboard
from cartera.services import generic_charts

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'cartera_ejemplo.xlsx')
User = get_user_model()


class AnalizarColumnasServiceTests(TestCase):
    def test_columna_numerica_es_apta_para_valor(self):
        df = pd.DataFrame({'saldo': [100, 200, 300], 'ciudad': ['Quito', 'Guayaquil', 'Quito']})
        resultado = generic_charts.analizar_columnas(df)
        columna_saldo = next(c for c in resultado['columnas'] if c['nombre'] == 'saldo')
        self.assertEqual(columna_saldo['tipo'], 'numerico')
        self.assertTrue(columna_saldo['apta_para_valor'])
        self.assertFalse(columna_saldo['apta_para_categoria'])

    def test_columna_texto_con_pocos_valores_distintos_es_apta_para_categoria(self):
        df = pd.DataFrame({'saldo': [100, 200, 300], 'ciudad': ['Quito', 'Guayaquil', 'Quito']})
        resultado = generic_charts.analizar_columnas(df)
        columna_ciudad = next(c for c in resultado['columnas'] if c['nombre'] == 'ciudad')
        self.assertEqual(columna_ciudad['tipo'], 'categorico')
        self.assertTrue(columna_ciudad['apta_para_categoria'])
        self.assertFalse(columna_ciudad['apta_para_valor'])

    def test_columna_tipo_identificador_no_es_apta_para_nada(self):
        df = pd.DataFrame({'id': ['A1', 'A2', 'A3'], 'saldo': [1, 2, 3]})
        resultado = generic_charts.analizar_columnas(df)
        columna_id = next(c for c in resultado['columnas'] if c['nombre'] == 'id')
        self.assertFalse(columna_id['apta_para_valor'])
        self.assertFalse(columna_id['apta_para_categoria'])
        self.assertIn('distintos', columna_id['motivo_no_apta'])

    def test_columna_con_demasiadas_categorias_no_es_apta(self):
        df = pd.DataFrame({'detalle': [f'texto único {i}' for i in range(60)], 'saldo': list(range(60))})
        resultado = generic_charts.analizar_columnas(df)
        columna_detalle = next(c for c in resultado['columnas'] if c['nombre'] == 'detalle')
        self.assertFalse(columna_detalle['apta_para_categoria'])

    def test_columna_vacia_no_es_apta_para_nada(self):
        df = pd.DataFrame({'vacia': [None, None, None], 'saldo': [1, 2, 3]})
        resultado = generic_charts.analizar_columnas(df)
        columna_vacia = next(c for c in resultado['columnas'] if c['nombre'] == 'vacia')
        self.assertEqual(columna_vacia['tipo'], 'vacio')
        self.assertFalse(columna_vacia['apta_para_valor'])
        self.assertFalse(columna_vacia['apta_para_categoria'])

    def test_columna_fecha_se_detecta_como_fecha(self):
        df = pd.DataFrame({'fecha': ['2026-01-01', '2026-02-01', '2026-03-01'], 'saldo': [1, 2, 3]})
        resultado = generic_charts.analizar_columnas(df)
        columna_fecha = next(c for c in resultado['columnas'] if c['nombre'] == 'fecha')
        self.assertEqual(columna_fecha['tipo'], 'fecha')


class GenerarRecomendacionesServiceTests(TestCase):
    def test_una_columna_numerica_sin_categorias_solo_recomienda_el_kpi_total(self):
        columnas = [
            {'nombre': 'saldo', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        self.assertEqual(len(recomendaciones), 1)
        self.assertEqual(recomendaciones[0], {
            'id': 'saldo::total', 'tipo_grafica': 'kpi', 'columna_valor': 'saldo', 'columna_categoria': None,
            'categorias_unicas': None, 'columna_serie_sugerida': None,
        })

    def test_columna_numerica_y_categorica_recomienda_kpi_y_grafica(self):
        columnas = [
            {'nombre': 'saldo', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10},
            {'nombre': 'ciudad', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': 5},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        tipos = [r['tipo_grafica'] for r in recomendaciones]
        self.assertEqual(tipos, ['kpi', 'chart'])
        self.assertEqual(recomendaciones[1]['columna_valor'], 'saldo')
        self.assertEqual(recomendaciones[1]['columna_categoria'], 'ciudad')
        self.assertEqual(recomendaciones[1]['categorias_unicas'], 5)

    def test_limita_las_categorias_recomendadas_por_cada_valor(self):
        columnas = [{'nombre': 'saldo', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10}]
        columnas += [
            {'nombre': f'cat{i}', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': i}
            for i in range(1, 6)  # 5 columnas de categoría disponibles
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        recomendaciones_de_grafica = [r for r in recomendaciones if r['tipo_grafica'] == 'chart']
        self.assertEqual(len(recomendaciones_de_grafica), generic_charts.MAX_CATEGORIAS_POR_VALOR)
        # Prioriza las de menor cardinalidad (gráficas más legibles).
        self.assertEqual([r['columna_categoria'] for r in recomendaciones_de_grafica], ['cat1', 'cat2', 'cat3'])

    def test_sin_columnas_numericas_no_recomienda_nada(self):
        columnas = [{'nombre': 'ciudad', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': 5}]
        self.assertEqual(generic_charts.generar_recomendaciones(columnas), [])


class CalcularDatosRecomendacionesServiceTests(TestCase):
    """Cada recomendación trae sus datos ya calculados, para que el frontend pueda mostrar una
    vista previa real de todas (sección "todos los generados deben de tener una forma de
    previsualizar") sin una solicitud aparte por cada una."""

    def test_agrega_los_datos_de_cada_recomendacion(self):
        df = pd.DataFrame({'saldo': [100, 300, 50], 'ciudad': ['Quito', 'Quito', 'Guayaquil']})
        columnas = generic_charts.analizar_columnas(df)['columnas']
        recomendaciones = generic_charts.generar_recomendaciones(columnas)

        con_datos = generic_charts.calcular_datos_recomendaciones(df, recomendaciones)

        kpi = next(r for r in con_datos if r['tipo_grafica'] == 'kpi')
        self.assertEqual(kpi['datos'], {'tipo': 'kpi', 'valor': 450.0})

        chart = next(r for r in con_datos if r['tipo_grafica'] == 'chart')
        self.assertEqual(chart['datos']['tipo'], 'chart')
        self.assertEqual(chart['datos']['categorias'][0], 'Quito')

    def test_no_pierde_los_campos_originales_de_la_recomendacion(self):
        df = pd.DataFrame({'saldo': [1, 2, 3]})
        recomendaciones = [{'id': 'saldo::total', 'tipo_grafica': 'kpi', 'columna_valor': 'saldo', 'columna_categoria': None, 'categorias_unicas': None}]
        con_datos = generic_charts.calcular_datos_recomendaciones(df, recomendaciones)
        self.assertEqual(con_datos[0]['id'], 'saldo::total')
        self.assertEqual(con_datos[0]['columna_valor'], 'saldo')


class AplicarSeleccionUsuarioServiceTests(TestCase):
    """El análisis automático nunca excluye una columna por sí solo — el usuario decide, columna
    por columna, marcándola como utilizable o no (sección "todas se muestren de forma
    obligatoria")."""

    def test_columna_marcada_queda_apta_segun_su_tipo(self):
        columnas = [
            {'nombre': 'saldo', 'tipo': 'numerico', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10},
            {'nombre': 'ciudad', 'tipo': 'categorico', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': 5},
        ]
        resultado = generic_charts.aplicar_seleccion_usuario(columnas, ['saldo', 'ciudad'])
        self.assertTrue(resultado[0]['apta_para_valor'])
        self.assertTrue(resultado[1]['apta_para_categoria'])

    def test_columna_no_marcada_queda_inapta_aunque_el_analisis_la_sugiriera(self):
        columnas = [{'nombre': 'saldo', 'tipo': 'numerico', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10}]
        resultado = generic_charts.aplicar_seleccion_usuario(columnas, [])
        self.assertFalse(resultado[0]['apta_para_valor'])
        self.assertFalse(resultado[0]['apta_para_categoria'])

    def test_columna_marcada_aunque_el_analisis_la_hubiera_descartado(self):
        """El usuario puede forzar como utilizable una columna que el análisis marcó
        `apta_para_categoria=False` (p. ej. por parecer un identificador)."""
        columnas = [{
            'nombre': 'codigo', 'tipo': 'categorico', 'apta_para_valor': False, 'apta_para_categoria': False,
            'valores_unicos': 15, 'motivo_no_apta': 'Todos los valores son distintos (parece un identificador).',
        }]
        resultado = generic_charts.aplicar_seleccion_usuario(columnas, ['codigo'])
        self.assertTrue(resultado[0]['apta_para_categoria'])

    def test_columna_vacia_marcada_por_el_usuario_no_rompe(self):
        columnas = [{'nombre': 'vacia', 'tipo': 'vacio', 'apta_para_valor': False, 'apta_para_categoria': False, 'valores_unicos': 0}]
        resultado = generic_charts.aplicar_seleccion_usuario(columnas, ['vacia'])
        self.assertTrue(resultado[0]['apta_para_categoria'])  # tipo != 'numerico' → rol de categoría
        self.assertFalse(resultado[0]['apta_para_valor'])


class GenerarDatosGraficaServiceTests(TestCase):
    def test_sin_categoria_devuelve_un_kpi_con_la_suma(self):
        df = pd.DataFrame({'saldo': [100, 200, 300]})
        resultado = generic_charts.generar_datos_grafica(df, 'saldo')
        self.assertEqual(resultado, {'tipo': 'kpi', 'valor': 600.0})

    def test_con_categoria_agrupa_y_suma_por_categoria(self):
        df = pd.DataFrame({'saldo': [100, 200, 50], 'ciudad': ['Quito', 'Quito', 'Guayaquil']})
        resultado = generic_charts.generar_datos_grafica(df, 'saldo', 'ciudad')
        self.assertEqual(resultado['tipo'], 'chart')
        self.assertEqual(resultado['categorias'][0], 'Quito')
        self.assertEqual(resultado['valores'][0], 300.0)

    def test_columna_de_valor_inexistente_devuelve_none(self):
        df = pd.DataFrame({'saldo': [1, 2, 3]})
        self.assertIsNone(generic_charts.generar_datos_grafica(df, 'no_existe'))

    def test_mas_de_15_categorias_se_agrupan_en_otras(self):
        filas = {'categoria': [f'cat-{i}' for i in range(20)], 'valor': [1] * 20}
        df = pd.DataFrame(filas)
        resultado = generic_charts.generar_datos_grafica(df, 'valor', 'categoria')
        self.assertEqual(len(resultado['categorias']), 16)  # 15 + "Otras"
        self.assertIn('Otras', resultado['categorias'])


class ColumnaSerieSugeridaServiceTests(TestCase):
    """Cada recomendación con categoría propone una segunda columna de agrupación (para barras
    agrupadas/apiladas) cuando hay otra columna categórica disponible."""

    def test_con_dos_columnas_de_categoria_sugiere_la_otra_como_serie(self):
        columnas = [
            {'nombre': 'saldo', 'tipo': 'numerico', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10},
            {'nombre': 'ciudad', 'tipo': 'categorico', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': 3},
            {'nombre': 'causal', 'tipo': 'categorico', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': 5},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        por_ciudad = next(r for r in recomendaciones if r['columna_categoria'] == 'ciudad')
        self.assertEqual(por_ciudad['columna_serie_sugerida'], 'causal')
        por_causal = next(r for r in recomendaciones if r['columna_categoria'] == 'causal')
        self.assertEqual(por_causal['columna_serie_sugerida'], 'ciudad')

    def test_con_una_sola_columna_de_categoria_no_hay_serie_sugerida(self):
        columnas = [
            {'nombre': 'saldo', 'tipo': 'numerico', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10},
            {'nombre': 'ciudad', 'tipo': 'categorico', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': 3},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        por_ciudad = next(r for r in recomendaciones if r['columna_categoria'] == 'ciudad')
        self.assertIsNone(por_ciudad['columna_serie_sugerida'])

    def test_el_kpi_de_total_nunca_tiene_serie_sugerida(self):
        columnas = [
            {'nombre': 'saldo', 'tipo': 'numerico', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10},
            {'nombre': 'ciudad', 'tipo': 'categorico', 'apta_para_valor': False, 'apta_para_categoria': True, 'valores_unicos': 3},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        kpi = next(r for r in recomendaciones if r['tipo_grafica'] == 'kpi')
        self.assertIsNone(kpi['columna_serie_sugerida'])


class GenerarDatosMultiserieServiceTests(TestCase):
    def test_agrupa_por_categoria_y_serie(self):
        df = pd.DataFrame({
            'saldo': [100, 200, 150, 50],
            'ciudad': ['Quito', 'Quito', 'Guayaquil', 'Guayaquil'],
            'causal': ['A', 'B', 'A', 'B'],
        })
        resultado = generic_charts.generar_datos_multiserie(df, 'saldo', 'ciudad', 'causal')
        self.assertEqual(resultado['tipo'], 'multiserie')
        self.assertEqual(set(resultado['categorias']), {'Quito', 'Guayaquil'})
        nombres_series = {s['nombre'] for s in resultado['series']}
        self.assertEqual(nombres_series, {'A', 'B'})

    def test_columna_inexistente_devuelve_none(self):
        df = pd.DataFrame({'saldo': [1, 2], 'ciudad': ['Quito', 'Guayaquil']})
        self.assertIsNone(generic_charts.generar_datos_multiserie(df, 'saldo', 'ciudad', 'no_existe'))

    def test_limita_las_series_a_las_de_mayor_total(self):
        filas = 20
        df = pd.DataFrame({
            'valor': [1] * filas,
            'categoria': ['cat-a'] * filas,
            'serie': [f'serie-{i}' for i in range(filas)],
        })
        resultado = generic_charts.generar_datos_multiserie(df, 'valor', 'categoria', 'serie')
        self.assertEqual(len(resultado['series']), generic_charts.MAX_SERIES_EN_GRAFICA)

    def test_mas_de_15_categorias_se_agrupan_en_otras(self):
        filas = 20
        df = pd.DataFrame({
            'valor': [1] * filas,
            'categoria': [f'cat-{i}' for i in range(filas)],
            'serie': ['A'] * filas,
        })
        resultado = generic_charts.generar_datos_multiserie(df, 'valor', 'categoria', 'serie')
        self.assertIn('Otras', resultado['categorias'])
        self.assertEqual(len(resultado['categorias']), 16)


class MejorParColumnasNumericasServiceTests(TestCase):
    def test_con_dos_o_mas_columnas_numericas_elige_las_de_menos_nulos(self):
        columnas_valor = [
            {'nombre': 'a', 'valores_no_nulos': 5},
            {'nombre': 'b', 'valores_no_nulos': 10},
            {'nombre': 'c', 'valores_no_nulos': 8},
        ]
        self.assertEqual(generic_charts._mejor_par_columnas_numericas(columnas_valor), ('b', 'c'))

    def test_con_menos_de_dos_columnas_numericas_devuelve_none(self):
        self.assertIsNone(generic_charts._mejor_par_columnas_numericas([{'nombre': 'a', 'valores_no_nulos': 5}]))
        self.assertIsNone(generic_charts._mejor_par_columnas_numericas([]))


class GenerarDatosDispersionServiceTests(TestCase):
    def test_calcula_los_puntos_x_y_de_cada_fila(self):
        df = pd.DataFrame({'ventas': [100, 200, 300], 'ganancia': [10, 25, 40]})
        resultado = generic_charts.generar_datos_dispersion(df, 'ventas', 'ganancia')
        self.assertEqual(resultado['tipo'], 'dispersion')
        self.assertEqual(resultado['puntos'], [
            {'x': 100.0, 'y': 10.0}, {'x': 200.0, 'y': 25.0}, {'x': 300.0, 'y': 40.0},
        ])

    def test_descarta_filas_con_algun_valor_faltante(self):
        df = pd.DataFrame({'ventas': [100, None, 300], 'ganancia': [10, 25, None]})
        resultado = generic_charts.generar_datos_dispersion(df, 'ventas', 'ganancia')
        self.assertEqual(resultado['puntos'], [{'x': 100.0, 'y': 10.0}])

    def test_columna_inexistente_devuelve_none(self):
        df = pd.DataFrame({'ventas': [1, 2]})
        self.assertIsNone(generic_charts.generar_datos_dispersion(df, 'ventas', 'no_existe'))

    def test_limita_la_cantidad_de_puntos(self):
        filas = generic_charts.LIMITE_PUNTOS_DISPERSION + 50
        df = pd.DataFrame({'x': list(range(filas)), 'y': list(range(filas))})
        resultado = generic_charts.generar_datos_dispersion(df, 'x', 'y')
        self.assertEqual(len(resultado['puntos']), generic_charts.LIMITE_PUNTOS_DISPERSION)


class RecomendacionDeDispersionServiceTests(TestCase):
    """Con al menos dos columnas numéricas disponibles, `generar_recomendaciones` propone además
    UNA gráfica de dispersión (`_mejor_par_columnas_numericas`) — no una por cada combinación
    posible."""

    def test_con_dos_columnas_numericas_agrega_una_recomendacion_de_dispersion(self):
        columnas = [
            {'nombre': 'ventas', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10, 'valores_no_nulos': 10},
            {'nombre': 'ganancia', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10, 'valores_no_nulos': 8},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        dispersion = next(r for r in recomendaciones if r['tipo_grafica'] == 'dispersion')
        self.assertEqual(dispersion['columna_valor'], 'ventas')
        self.assertEqual(dispersion['columna_valor_y'], 'ganancia')
        self.assertIsNone(dispersion['columna_categoria'])

    def test_con_una_sola_columna_numerica_no_hay_recomendacion_de_dispersion(self):
        columnas = [
            {'nombre': 'ventas', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 10, 'valores_no_nulos': 10},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        self.assertFalse(any(r['tipo_grafica'] == 'dispersion' for r in recomendaciones))

    def test_calcular_datos_recomendaciones_calcula_los_puntos_de_la_dispersion(self):
        df = pd.DataFrame({'ventas': [100, 200], 'ganancia': [10, 20]})
        columnas = [
            {'nombre': 'ventas', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 2, 'valores_no_nulos': 2},
            {'nombre': 'ganancia', 'apta_para_valor': True, 'apta_para_categoria': False, 'valores_unicos': 2, 'valores_no_nulos': 2},
        ]
        recomendaciones = generic_charts.generar_recomendaciones(columnas)
        con_datos = generic_charts.calcular_datos_recomendaciones(df, recomendaciones)
        dispersion = next(r for r in con_datos if r['tipo_grafica'] == 'dispersion')
        self.assertEqual(dispersion['datos']['tipo'], 'dispersion')
        self.assertEqual(len(dispersion['datos']['puntos']), 2)
        self.assertIsNone(dispersion['datos_multiserie'])


class FlujoApiAnalizarRecomendarYAgregarTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        usuario = User.objects.create_superuser(username='tester_charts', email='tc@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas')

    def _subir_archivo(self):
        with open(FIXTURE_PATH, 'rb') as f:
            resp = self.client.post('/api/cartera/validar-archivo', {'archivo': f, 'dashboard_id': 'finanzas'}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        return resp.json()['carga_id']

    def test_analizar_columnas_devuelve_columnas_aptas_para_valor_y_categoria(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/analizar-columnas', {'carga_id': carga_id}, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['total_filas'], 15)
        columna_saldo = next(c for c in data['columnas'] if c['nombre'] == 'Saldo')
        self.assertTrue(columna_saldo['apta_para_valor'])

    def test_analizar_columnas_sin_carga_id_devuelve_400(self):
        resp = self.client.post('/api/cartera/analizar-columnas', {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_recomendar_graficas_devuelve_recomendaciones_a_partir_del_archivo(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/recomendar-graficas', {'carga_id': carga_id}, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(len(data['recomendaciones']) > 0)
        recomendacion_saldo_total = next(r for r in data['recomendaciones'] if r['id'] == 'Saldo::total')
        self.assertEqual(recomendacion_saldo_total['tipo_grafica'], 'kpi')
        # Cada recomendación trae sus datos ya calculados, para poder previsualizarla sin una
        # solicitud aparte.
        self.assertIn('datos', recomendacion_saldo_total)
        self.assertEqual(recomendacion_saldo_total['datos']['tipo'], 'kpi')
        self.assertIsInstance(recomendacion_saldo_total['datos']['valor'], float)

    def test_recomendar_graficas_respeta_las_columnas_utilizables_del_usuario(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/recomendar-graficas', {
            'carga_id': carga_id, 'columnas_utilizables': ['Saldo'],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Solo "Saldo" fue marcada utilizable: ninguna recomendación debe agrupar por otra columna.
        self.assertTrue(all(r['columna_categoria'] is None for r in data['recomendaciones']))
        self.assertTrue(any(r['id'] == 'Saldo::total' for r in data['recomendaciones']))

    def test_recomendar_graficas_sin_columnas_utilizables_no_recomienda_nada(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/recomendar-graficas', {
            'carga_id': carga_id, 'columnas_utilizables': [],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['recomendaciones'], [])

    def test_recomendar_graficas_no_borra_el_archivo_temporal(self):
        """El archivo debe seguir disponible para poder agregar varias gráficas después de
        recomendar (a diferencia del viejo `generar-dashboard`, que era una acción terminal)."""
        carga_id = self._subir_archivo()
        self.client.post('/api/cartera/recomendar-graficas', {'carga_id': carga_id}, format='json')
        carga = CargaArchivo.objects.get(id=carga_id)
        self.assertNotEqual(carga.archivo_temp_nombre, '')

    def test_agregar_grafica_crea_el_componente_y_marca_la_carga_procesada(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Cartera total', 'columna_valor': 'Saldo',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(len(data['components']), 1)

        carga = CargaArchivo.objects.get(id=carga_id)
        self.assertEqual(carga.estado, CargaArchivo.Estado.PROCESADO)
        # A diferencia del viejo flujo, el archivo temporal se conserva: puede haber más
        # gráficas por agregar desde la misma carga.
        self.assertNotEqual(carga.archivo_temp_nombre, '')

    def test_agregar_dos_graficas_de_la_misma_carga_se_suman(self):
        carga_id = self._subir_archivo()
        self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Cartera total', 'columna_valor': 'Saldo',
        }, format='json')
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por causal', 'columna_valor': 'Saldo', 'columna_categoria': 'Causal',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        titulos = sorted(c['content']['titulo'] for c in resp.json()['components'])
        self.assertEqual(titulos, ['Cartera total', 'Saldo por causal'])

    def test_agregar_grafica_respeta_el_tipo_de_visualizacion_elegido(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por causal', 'columna_valor': 'Saldo',
            'columna_categoria': 'Causal', 'tipo_visualizacion': 'pastel',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['chart_type'], 'pastel')
        self.assertEqual(componente['type'], 'chart')

    def test_agregar_grafica_con_tipo_kpi_ignora_la_categoria_y_suma_el_total(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Total de saldo', 'columna_valor': 'Saldo',
            'columna_categoria': 'Causal', 'tipo_visualizacion': 'kpi',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['type'], 'kpi')
        self.assertIn('valor', componente['content'])
        self.assertNotIn('categorias', componente['content'])

    def test_agregar_grafica_agrupada_calcula_datos_multiserie(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por ciudad y causal', 'columna_valor': 'Saldo',
            'columna_categoria': 'Lugar Geográfico', 'columna_serie': 'Causal', 'tipo_visualizacion': 'barras_agrupadas',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['chart_type'], 'barras_agrupadas')
        self.assertIn('series', componente['content'])
        self.assertIn('categorias', componente['content'])

    def test_agregar_grafica_sin_descripcion_guarda_descripcion_vacia(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Cartera total', 'columna_valor': 'Saldo',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['content']['descripcion'], '')

    def test_agregar_grafica_con_descripcion_la_guarda_en_el_contenido(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por causal', 'columna_valor': 'Saldo',
            'columna_categoria': 'Causal', 'descripcion': 'Distribución del saldo por causal.',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['content']['descripcion'], 'Distribución del saldo por causal.')

    def test_agregar_grafica_pastel_incluye_posicion_de_leyenda_por_defecto(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por causal', 'columna_valor': 'Saldo',
            'columna_categoria': 'Causal', 'tipo_visualizacion': 'pastel',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['config']['leyenda_posicion'], 'abajo')

    def test_agregar_grafica_barras_horizontales_no_incluye_posicion_de_leyenda(self):
        """Las gráficas de una sola serie no dibujan leyenda, así que no necesitan la config."""
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por causal', 'columna_valor': 'Saldo',
            'columna_categoria': 'Causal', 'tipo_visualizacion': 'barras_horizontales',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertNotIn('leyenda_posicion', componente['config'])

    def test_agregar_grafica_agrupada_incluye_posicion_de_leyenda_por_defecto(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por ciudad y causal', 'columna_valor': 'Saldo',
            'columna_categoria': 'Lugar Geográfico', 'columna_serie': 'Causal', 'tipo_visualizacion': 'barras_agrupadas',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['config']['leyenda_posicion'], 'abajo')

    def test_agregar_grafica_apilada_sin_columna_serie_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo apilado', 'columna_valor': 'Saldo',
            'columna_categoria': 'Lugar Geográfico', 'tipo_visualizacion': 'barras_apiladas',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLUMNA_SERIE_REQUERIDA')

    def test_agregar_grafica_area_apilada_calcula_datos_multiserie_e_incluye_leyenda(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo por ciudad y causal (área)', 'columna_valor': 'Saldo',
            'columna_categoria': 'Lugar Geográfico', 'columna_serie': 'Causal', 'tipo_visualizacion': 'area_apilada',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['chart_type'], 'area_apilada')
        self.assertIn('series', componente['content'])
        self.assertEqual(componente['config']['leyenda_posicion'], 'abajo')

    def test_agregar_grafica_dispersion_calcula_los_puntos(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo vs. Dias credito', 'columna_valor': 'Saldo',
            'columna_valor_y': 'Dias credito', 'tipo_visualizacion': 'dispersion',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        componente = resp.json()['components'][0]
        self.assertEqual(componente['chart_type'], 'dispersion')
        self.assertEqual(componente['type'], 'chart')
        self.assertIn('puntos', componente['content'])
        self.assertTrue(len(componente['content']['puntos']) > 0)

    def test_agregar_grafica_dispersion_sin_columna_valor_y_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Saldo vs. nada', 'columna_valor': 'Saldo',
            'tipo_visualizacion': 'dispersion',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLUMNA_VALOR_Y_REQUERIDA')

    def test_agregar_grafica_sin_titulo_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'columna_valor': 'Saldo',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'TITULO_REQUERIDO')

    def test_agregar_grafica_con_columna_invalida_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'X', 'columna_valor': 'no_existe',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLUMNA_INVALIDA')

    def test_reemplazar_existentes_en_una_carga_nueva_no_mezcla_datos_de_dos_archivos(self):
        carga_id = self._subir_archivo()
        self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id, 'titulo': 'Primera', 'columna_valor': 'Saldo',
        }, format='json')

        carga_id_2 = self._subir_archivo()
        resp = self.client.post('/api/cartera/agregar-grafica', {
            'carga_id': carga_id_2, 'titulo': 'Segunda', 'columna_valor': 'Saldo', 'reemplazar_existentes': True,
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        titulos = [c['content']['titulo'] for c in resp.json()['components']]
        self.assertEqual(titulos, ['Segunda'])
