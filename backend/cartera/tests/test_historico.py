"""Histórico de archivos cargados (sección 28): `services/historico.py` y las vistas
`HistoricoCargasView`/`HistoricoTablaView`."""

import os

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from cartera.models import CargaArchivo, Dashboard, FilaArchivoHistorico
from cartera.services import dashboards as dashboards_service
from cartera.services import historico, plantilla

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'cartera_ejemplo.xlsx')
User = get_user_model()


def _crear_carga(dashboard_id='finanzas', subido_por=None):
    return CargaArchivo.objects.create(dashboard_id=dashboard_id, nombre_original='datos.xlsx', subido_por=subido_por)


def _guardar_todo(carga, df):
    """Atajo para los tests que no les interesa la feature de "solo columnas históricas": guarda
    TODAS las columnas del DataFrame como históricas, replicando el comportamiento previo a esa
    feature (fila completa)."""
    historico.guardar_filas_historicas(carga, df, list(df.columns))


class GuardarFilasHistoricasServiceTests(TestCase):
    def test_persiste_una_fila_historica_por_fila_del_dataframe(self):
        carga = _crear_carga()
        df = pd.DataFrame({'producto': ['A', 'B'], 'ventas': [100, 200]})

        _guardar_todo(carga, df)

        filas = list(FilaArchivoHistorico.objects.filter(carga=carga).order_by('orden'))
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0].datos, {'producto': 'A', 'ventas': 100})
        self.assertEqual(filas[1].datos, {'producto': 'B', 'ventas': 200})

    def test_reaplicar_la_misma_carga_reemplaza_en_vez_de_duplicar(self):
        carga = _crear_carga()
        _guardar_todo(carga, pd.DataFrame({'ventas': [100]}))
        _guardar_todo(carga, pd.DataFrame({'ventas': [200, 300]}))

        filas = list(FilaArchivoHistorico.objects.filter(carga=carga).order_by('orden'))
        self.assertEqual(len(filas), 2)
        self.assertEqual([f.datos['ventas'] for f in filas], [200, 300])

    def test_valores_faltantes_se_guardan_como_null(self):
        carga = _crear_carga()
        df = pd.DataFrame({'ventas': [100, None]})

        _guardar_todo(carga, df)

        filas = list(FilaArchivoHistorico.objects.filter(carga=carga).order_by('orden'))
        self.assertIsNone(filas[1].datos['ventas'])

    def test_solo_guarda_las_columnas_marcadas_como_historicas(self):
        carga = _crear_carga()
        df = pd.DataFrame({'producto': ['A', 'B'], 'ventas': [100, 200], 'costo': [50, 60]})

        historico.guardar_filas_historicas(carga, df, ['ventas'])

        filas = list(FilaArchivoHistorico.objects.filter(carga=carga).order_by('orden'))
        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[0].datos, {'ventas': 100})
        self.assertEqual(filas[1].datos, {'ventas': 200})

    def test_lista_vacia_no_guarda_ninguna_fila(self):
        carga = _crear_carga()
        historico.guardar_filas_historicas(carga, pd.DataFrame({'ventas': [100, 200]}), [])
        self.assertFalse(FilaArchivoHistorico.objects.filter(carga=carga).exists())

    def test_una_columna_marcada_que_ya_no_existe_en_el_archivo_se_ignora(self):
        carga = _crear_carga()
        df = pd.DataFrame({'ventas': [100]})

        historico.guardar_filas_historicas(carga, df, ['ventas', 'columna_que_no_existe'])

        filas = list(FilaArchivoHistorico.objects.filter(carga=carga))
        self.assertEqual(filas[0].datos, {'ventas': 100})

    def test_reaplicar_con_una_lista_distinta_de_columnas_reemplaza_las_anteriores(self):
        carga = _crear_carga()
        historico.guardar_filas_historicas(carga, pd.DataFrame({'ventas': [100], 'costo': [50]}), ['ventas', 'costo'])
        historico.guardar_filas_historicas(carga, pd.DataFrame({'ventas': [100], 'costo': [50]}), ['ventas'])

        filas = list(FilaArchivoHistorico.objects.filter(carga=carga))
        self.assertEqual(filas[0].datos, {'ventas': 100})


class ColumnasHistoricasConfiguradasServiceTests(TestCase):
    def test_establecer_y_leer(self):
        historico.establecer_columnas_historicas('finanzas', ['Ventas', 'Costo'])
        self.assertEqual(set(historico.columnas_historicas_configuradas('finanzas')), {'Ventas', 'Costo'})

    def test_establecer_reemplaza_la_configuracion_previa_en_vez_de_acumular(self):
        historico.establecer_columnas_historicas('finanzas', ['Ventas', 'Costo'])
        historico.establecer_columnas_historicas('finanzas', ['Ventas'])
        self.assertEqual(historico.columnas_historicas_configuradas('finanzas'), ['Ventas'])

    def test_lista_vacia_deja_la_configuracion_sin_ninguna_columna(self):
        historico.establecer_columnas_historicas('finanzas', ['Ventas'])
        historico.establecer_columnas_historicas('finanzas', [])
        self.assertEqual(historico.columnas_historicas_configuradas('finanzas'), [])

    def test_no_afecta_la_configuracion_de_otro_dashboard(self):
        historico.establecer_columnas_historicas('finanzas', ['Ventas'])
        historico.establecer_columnas_historicas('comercial', ['Costo'])
        self.assertEqual(historico.columnas_historicas_configuradas('finanzas'), ['Ventas'])

    def test_sin_configurar_devuelve_lista_vacia(self):
        self.assertEqual(historico.columnas_historicas_configuradas('finanzas'), [])


class CascadaBorradoTests(TestCase):
    def test_borrar_la_carga_borra_sus_filas_historicas(self):
        carga = _crear_carga()
        _guardar_todo(carga, pd.DataFrame({'ventas': [100]}))

        carga.delete()

        self.assertFalse(FilaArchivoHistorico.objects.filter(carga_id=carga.id).exists())

    def test_eliminar_dashboard_borra_las_filas_historicas_de_sus_cargas(self):
        dashboard = dashboards_service.crear_dashboard(nombre='Comercial')
        carga = CargaArchivo.objects.create(dashboard_id=dashboard.dashboard_id, nombre_original='datos.xlsx')
        _guardar_todo(carga, pd.DataFrame({'ventas': [100]}))

        dashboards_service.eliminar_dashboard(dashboard.dashboard_id, confirmacion_nombre='Comercial')

        self.assertFalse(FilaArchivoHistorico.objects.filter(carga_id=carga.id).exists())


class CalcularTablaHistoricaServiceTests(TestCase):
    def setUp(self):
        self.carga_enero = _crear_carga()
        self.carga_febrero = _crear_carga()
        _guardar_todo(self.carga_enero, pd.DataFrame({
            'producto': ['A', 'B', 'C'], 'ventas': [100, 200, 300], 'cliente': ['x', 'y', 'x'],
        }))
        _guardar_todo(self.carga_febrero, pd.DataFrame({
            'producto': ['A', 'B'], 'ventas': [500, 500],
        }))

    def test_suma_una_fila_por_carga_en_orden_cronologico(self):
        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'ventas', 'tipo_agregacion': 'suma'}],
        )
        self.assertEqual(resultado['columnas'], ['Archivo', 'Usuario', 'Fecha de carga', 'Fecha de corte', 'ventas'])
        self.assertEqual(len(resultado['filas']), 2)
        self.assertEqual(resultado['filas'][0][-1], 600.0)  # enero: 100+200+300
        self.assertEqual(resultado['filas'][1][-1], 1000.0)  # febrero: 500+500

    def test_columna_usuario_muestra_quien_subio_cada_carga(self):
        ana = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        carga_con_usuario = _crear_carga(subido_por=ana)
        carga_sin_usuario = _crear_carga()
        _guardar_todo(carga_con_usuario, pd.DataFrame({'ventas': [1]}))
        _guardar_todo(carga_sin_usuario, pd.DataFrame({'ventas': [2]}))

        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'ventas', 'tipo_agregacion': 'suma'}],
            carga_ids=[str(carga_con_usuario.id), str(carga_sin_usuario.id)],
        )

        indice_usuario = resultado['columnas'].index('Usuario')
        usuarios = [fila[indice_usuario] for fila in resultado['filas']]
        self.assertIn('ana', usuarios)
        self.assertIn('Desconocido', usuarios)

    def test_promedio(self):
        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'ventas', 'tipo_agregacion': 'promedio'}],
        )
        self.assertAlmostEqual(resultado['filas'][0][-1], 200.0)  # (100+200+300)/3
        self.assertAlmostEqual(resultado['filas'][1][-1], 500.0)

    def test_conteo_unicos(self):
        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'cliente', 'tipo_agregacion': 'conteo_unicos'}],
        )
        self.assertEqual(resultado['filas'][0][-1], 2.0)  # 'x', 'y' en enero
        self.assertEqual(resultado['filas'][1][-1], 0.0)  # 'cliente' no existe en febrero

    def test_carga_ids_filtra_a_solo_las_cargas_pedidas(self):
        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'ventas', 'tipo_agregacion': 'suma'}], carga_ids=[str(self.carga_enero.id)],
        )
        self.assertEqual(len(resultado['filas']), 1)
        self.assertEqual(resultado['filas'][0][-1], 600.0)

    def test_dos_columnas_con_distinto_tipo_de_agregacion(self):
        resultado = historico.calcular_tabla_historica('finanzas', [
            {'columna': 'ventas', 'tipo_agregacion': 'suma'},
            {'columna': 'ventas', 'tipo_agregacion': 'promedio'},
        ])
        self.assertEqual(resultado['filas'][0][-2], 600.0)
        self.assertAlmostEqual(resultado['filas'][0][-1], 200.0)

    def test_valor_celda_muestra_el_valor_cuando_es_igual_en_toda_la_carga(self):
        carga = _crear_carga()
        _guardar_todo(carga, pd.DataFrame({'zona': ['Norte', 'Norte', 'Norte']}))
        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'zona', 'tipo_agregacion': 'valor_celda'}], carga_ids=[str(carga.id)],
        )
        self.assertEqual(resultado['filas'][0][-1], 'Norte')

    def test_valor_celda_muestra_varios_cuando_la_carga_tiene_valores_distintos(self):
        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'cliente', 'tipo_agregacion': 'valor_celda'}], carga_ids=[str(self.carga_enero.id)],
        )
        self.assertEqual(resultado['filas'][0][-1], 'Varios')  # cliente: x, y, x -> distintos

    def test_valor_celda_en_columna_que_no_existe_para_esa_carga_queda_none(self):
        resultado = historico.calcular_tabla_historica(
            'finanzas', [{'columna': 'cliente', 'tipo_agregacion': 'valor_celda'}], carga_ids=[str(self.carga_febrero.id)],
        )
        self.assertIsNone(resultado['filas'][0][-1])


class ListarCargasHistoricasServiceTests(TestCase):
    def test_solo_incluye_cargas_con_filas_historicas(self):
        con_historico = _crear_carga()
        _guardar_todo(con_historico, pd.DataFrame({'ventas': [1]}))
        _crear_carga()  # nunca se aplicó a la plantilla -> sin filas históricas

        resultado = historico.listar_cargas_historicas('finanzas')

        self.assertEqual(len(resultado['cargas']), 1)
        self.assertEqual(resultado['cargas'][0]['carga_id'], str(con_historico.id))

    def test_columnas_disponibles_es_la_configuracion_de_columnas_historicas_no_lo_guardado(self):
        # Aunque las filas guardadas tengan columnas distintas (p. ej. cargas de antes de esta
        # config, que persisten la fila completa), `columnas_disponibles` debe reflejar solo lo que
        # el usuario marcó a propósito como histórico — no lo que haya en `FilaArchivoHistorico`.
        carga_1 = _crear_carga()
        carga_2 = _crear_carga()
        _guardar_todo(carga_1, pd.DataFrame({'ventas': [1], 'costo': [1]}))
        _guardar_todo(carga_2, pd.DataFrame({'ventas': [1], 'unidades': [1]}))
        historico.establecer_columnas_historicas('finanzas', ['ventas'])

        resultado = historico.listar_cargas_historicas('finanzas')

        self.assertEqual(resultado['columnas_disponibles'], ['ventas'])

    def test_sin_columnas_historicas_configuradas_columnas_disponibles_queda_vacia(self):
        carga = _crear_carga()
        _guardar_todo(carga, pd.DataFrame({'ventas': [1], 'costo': [1]}))

        resultado = historico.listar_cargas_historicas('finanzas')

        self.assertEqual(resultado['columnas_disponibles'], [])

    def test_sin_ninguna_carga_historica_devuelve_listas_vacias(self):
        resultado = historico.listar_cargas_historicas('sin-datos')
        self.assertEqual(resultado, {'cargas': [], 'columnas_disponibles': []})


class ObtenerFilasArchivoServiceTests(TestCase):
    def test_devuelve_todas_las_columnas_y_filas_sin_agregar(self):
        carga = _crear_carga()
        _guardar_todo(carga, pd.DataFrame({
            'producto': ['A', 'B', 'C'], 'ventas': [100, 200, 300],
        }))

        resultado = historico.obtener_filas_archivo(carga)

        self.assertEqual(resultado['columnas'], ['producto', 'ventas'])
        self.assertEqual(resultado['filas'], [['A', 100], ['B', 200], ['C', 300]])

    def test_respeta_el_orden_original_de_las_filas(self):
        carga = _crear_carga()
        _guardar_todo(carga, pd.DataFrame({'producto': ['Z', 'A', 'M']}))

        resultado = historico.obtener_filas_archivo(carga)

        self.assertEqual([f[0] for f in resultado['filas']], ['Z', 'A', 'M'])

    def test_carga_sin_filas_historicas_devuelve_listas_vacias(self):
        carga = _crear_carga()
        resultado = historico.obtener_filas_archivo(carga)
        self.assertEqual(resultado, {'columnas': [], 'filas': []})


class HistoricoViewsApiTests(TestCase):
    """Extremo a extremo: subir y aplicar dos archivos reales al mismo dashboard y consultar el
    histórico resultante a través de las vistas."""

    def setUp(self):
        self.client = APIClient()
        usuario = User.objects.create_superuser(username='tester_historico', email='th@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas')
        plantilla.sembrar_plantilla('finanzas')

    def _subir_y_aplicar(self, columnas_historicas=None):
        """Por defecto marca TODAS las columnas del archivo como históricas — preserva el
        comportamiento previo a la feature de columnas históricas (fila completa) para los tests
        que no les interesa esa selección puntualmente."""
        with open(FIXTURE_PATH, 'rb') as f:
            resp = self.client.post('/api/cartera/validar-archivo', {'archivo': f, 'dashboard_id': 'finanzas'}, format='multipart')
        carga_id = resp.json()['carga_id']
        sugerido = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json').json()
        if columnas_historicas is None:
            columnas_historicas = [c['nombre'] for c in sugerido['columnas']]
        self.client.post('/api/cartera/plantilla/aplicar', {
            'carga_id': carga_id, 'mapeo': sugerido['mapeo'], 'columnas_historicas': columnas_historicas,
        }, format='json')
        return carga_id

    def test_aplicar_mapeo_guarda_filas_historicas(self):
        carga_id = self._subir_y_aplicar()
        self.assertTrue(FilaArchivoHistorico.objects.filter(carga_id=carga_id).exists())

    def test_aplicar_solo_guarda_las_columnas_marcadas_como_historicas(self):
        carga_id = self._subir_y_aplicar(columnas_historicas=['Saldo'])
        carga = CargaArchivo.objects.get(id=carga_id)
        resultado = historico.obtener_filas_archivo(carga)
        self.assertEqual(resultado['columnas'], ['Saldo'])

    def test_aplicar_persiste_la_configuracion_para_reconocerla_en_la_proxima_carga(self):
        self._subir_y_aplicar(columnas_historicas=['Saldo', 'Telefono'])
        resp = self.client.get('/api/cartera/historico/cargas', {'dashboard_id': 'finanzas'})
        self.assertEqual(set(resp.json()['columnas_historicas_configuradas']), {'Saldo', 'Telefono'})

    def test_aplicar_de_nuevo_con_otra_seleccion_reemplaza_la_configuracion_anterior(self):
        self._subir_y_aplicar(columnas_historicas=['Saldo'])
        self._subir_y_aplicar(columnas_historicas=['Telefono'])
        resp = self.client.get('/api/cartera/historico/cargas', {'dashboard_id': 'finanzas'})
        self.assertEqual(resp.json()['columnas_historicas_configuradas'], ['Telefono'])

    def test_listar_cargas_requiere_dashboard_id(self):
        resp = self.client.get('/api/cartera/historico/cargas')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'DASHBOARD_ID_REQUERIDO')

    def test_listar_cargas_devuelve_la_carga_aplicada(self):
        carga_id = self._subir_y_aplicar()
        resp = self.client.get('/api/cartera/historico/cargas', {'dashboard_id': 'finanzas'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['cargas']), 1)
        self.assertEqual(data['cargas'][0]['carga_id'], carga_id)
        self.assertIn('Saldo', data['columnas_disponibles'])

    def test_tabla_historica_agrega_saldo(self):
        # Suma de "Saldo" sobre las 15 filas del archivo tal cual se subieron (esta tabla NO
        # descarta filas inválidas como sí hace el flujo clásico de cartera — son pipelines
        # independientes; por eso el número no coincide con el KPI "cartera_total" de ese otro
        # flujo). 13 de las 15 filas tienen un Saldo numérico; `pd.to_numeric(errors='coerce')`
        # excluye las otras 2 automáticamente al sumar.
        self._subir_y_aplicar()
        resp = self.client.post('/api/cartera/historico/tabla', {
            'dashboard_id': 'finanzas', 'columnas_valor': [{'columna': 'Saldo', 'tipo_agregacion': 'suma'}],
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['columnas'], ['Archivo', 'Usuario', 'Fecha de carga', 'Fecha de corte', 'Saldo'])
        self.assertEqual(len(data['filas']), 1)
        self.assertEqual(data['filas'][0][1], 'tester_historico')  # quien subió el archivo en _subir_y_aplicar
        self.assertAlmostEqual(data['filas'][0][-1], 7401.25, places=2)

    def test_sin_acceso_al_dashboard_devuelve_403(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/cartera/historico/cargas', {'dashboard_id': 'finanzas'})
        self.assertIn(resp.status_code, (401, 403))

    def test_ver_archivo_devuelve_todas_las_columnas_y_filas_de_esa_carga(self):
        carga_id = self._subir_y_aplicar()
        resp = self.client.get(f'/api/cartera/historico/cargas/{carga_id}/archivo')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('Saldo', data['columnas'])
        self.assertEqual(len(data['filas']), 15)

    def test_ver_archivo_sin_acceso_al_dashboard_devuelve_403(self):
        carga_id = self._subir_y_aplicar()
        self.client.force_authenticate(user=None)
        resp = self.client.get(f'/api/cartera/historico/cargas/{carga_id}/archivo')
        self.assertIn(resp.status_code, (401, 403))
