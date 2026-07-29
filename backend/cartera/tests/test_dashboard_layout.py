import json
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from cartera import permisos
from cartera.models import DashboardAuditLog, DashboardComponent, DashboardLayout
from cartera.services import dashboard_layout as dl


class LayoutPorDefectoTests(TestCase):
    def test_get_crea_layout_por_defecto(self):
        client = APIClient()
        resp = client.get('/api/dashboards/cartera/layout')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['version'], 1)
        self.assertEqual(len(data['components']), 17)
        self.assertTrue(DashboardLayout.objects.filter(dashboard_id='cartera').exists())

    def test_dashboard_no_reconocido_da_error(self):
        client = APIClient()
        resp = client.get('/api/dashboards/inexistente/layout')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'DASHBOARD_NO_ENCONTRADO')


class GuardarLayoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.data_inicial = self.client.get('/api/dashboards/cartera/layout').json()

    def _guardar(self, componentes, version=None, changed_by='Tester'):
        payload = {'version': version if version is not None else self.data_inicial['version'], 'components': componentes, 'changed_by': changed_by}
        return self.client.put('/api/dashboards/cartera/layout', data=json.dumps(payload), content_type='application/json')

    def test_guarda_cambio_de_orden_tamano_color_y_texto(self):
        comps = self.data_inicial['components']
        for c in comps:
            if c['component_id'] == 'kpi-cartera-vencida':
                c['order'] = 10
            if c['component_id'] == 'chart-top-clientes':
                c['content']['titulo'] = 'Mis mejores clientes'
                c['styles'] = {'colorPrincipal': '#123456'}
                c['width'] = 8

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['version'], 2)

        audit = list(DashboardAuditLog.objects.filter(dashboard_id='cartera').values_list('component_id', 'change_type'))
        self.assertIn(('kpi-cartera-vencida', DashboardAuditLog.TipoCambio.ORDEN), audit)
        self.assertIn(('chart-top-clientes', DashboardAuditLog.TipoCambio.TEXTO), audit)
        self.assertIn(('chart-top-clientes', DashboardAuditLog.TipoCambio.COLOR), audit)
        self.assertIn(('chart-top-clientes', DashboardAuditLog.TipoCambio.TAMANO), audit)

    def test_ocultar_componente_registra_auditoria(self):
        comps = self.data_inicial['components']
        for c in comps:
            if c['component_id'] == 'kpi-mayor-360':
                c['is_visible'] = False

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        oculto = next(c for c in resp.json()['components'] if c['component_id'] == 'kpi-mayor-360')
        self.assertFalse(oculto['is_visible'])
        self.assertTrue(DashboardAuditLog.objects.filter(
            dashboard_id='cartera', component_id='kpi-mayor-360', change_type=DashboardAuditLog.TipoCambio.OCULTADO,
        ).exists())

    def test_titulo_con_signo_mayor_que_no_se_corrompe(self):
        """Regresión: la sanitización no debe destruir texto legítimo como 'Cartera > 120 días'."""
        comps = self.data_inicial['components']
        kpi = next(c for c in comps if c['component_id'] == 'kpi-mayor-120')
        self.assertIn('>', kpi['content']['titulo'])

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        kpi_guardado = next(c for c in resp.json()['components'] if c['component_id'] == 'kpi-mayor-120')
        self.assertEqual(kpi_guardado['content']['titulo'], kpi['content']['titulo'])

    def test_sanitiza_etiquetas_html_del_titulo(self):
        comps = self.data_inicial['components']
        for c in comps:
            if c['component_id'] == 'chart-top-clientes':
                c['content']['titulo'] = '<script>alert(1)</script>Top clientes'

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        guardado = next(c for c in resp.json()['components'] if c['component_id'] == 'chart-top-clientes')
        self.assertNotIn('<script>', guardado['content']['titulo'])
        self.assertIn('Top clientes', guardado['content']['titulo'])

    def test_conflicto_de_version_no_sobrescribe(self):
        comps = self.data_inicial['components']
        resp1 = self._guardar(comps, version=self.data_inicial['version'])
        self.assertEqual(resp1.status_code, 200)

        resp2 = self._guardar(comps, version=self.data_inicial['version'])
        self.assertEqual(resp2.status_code, 409)
        self.assertEqual(resp2.json()['error'], 'CONFLICTO_DE_VERSION')

    def test_rechaza_componente_desconocido(self):
        resp = self._guardar([{'component_id': 'kpi-hackeado', 'row': 1, 'order': 1, 'width': 2, 'height': 180}])
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COMPONENTE_NO_PERMITIDO')

    def test_rechaza_ancho_fuera_de_rango(self):
        comps = self.data_inicial['components']
        comps[0]['width'] = 13
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'ANCHO_INVALIDO')

    def test_rechaza_color_invalido(self):
        comps = self.data_inicial['components']
        for c in comps:
            if c['component_id'] == 'chart-top-clientes':
                c['styles'] = {'colorPrincipal': 'javascript:alert(1)'}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLOR_INVALIDO')

    def test_acepta_color_hex_y_rgba(self):
        comps = self.data_inicial['components']
        for c in comps:
            if c['component_id'] == 'chart-top-clientes':
                c['styles'] = {'colorPrincipal': '#1F4E78', 'colorVencido': 'rgba(198, 40, 40, 0.8)'}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)


class RestablecerLayoutTests(TestCase):
    def test_restablecer_recupera_visibilidad_y_registra_auditoria(self):
        client = APIClient()
        data = client.get('/api/dashboards/cartera/layout').json()
        comps = data['components']
        for c in comps:
            if c['component_id'] == 'kpi-mayor-360':
                c['is_visible'] = False
        client.put('/api/dashboards/cartera/layout', data=json.dumps({'version': data['version'], 'components': comps}), content_type='application/json')

        resp = client.post('/api/dashboards/cartera/layout/reset', data=json.dumps({'changed_by': 'Admin'}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        nuevo = resp.json()
        kpi = next(c for c in nuevo['components'] if c['component_id'] == 'kpi-mayor-360')
        self.assertTrue(kpi['is_visible'])
        self.assertTrue(DashboardAuditLog.objects.filter(
            dashboard_id='cartera', change_type=DashboardAuditLog.TipoCambio.RESTABLECIDO,
        ).exists())

    def test_versions_devuelve_historial_mas_reciente_primero(self):
        client = APIClient()
        client.get('/api/dashboards/cartera/layout')
        client.post('/api/dashboards/cartera/layout/reset', data=json.dumps({'changed_by': 'A'}), content_type='application/json')
        client.post('/api/dashboards/cartera/layout/reset', data=json.dumps({'changed_by': 'B'}), content_type='application/json')

        resp = client.get('/api/dashboards/cartera/versions')
        entradas = resp.json()
        self.assertGreaterEqual(len(entradas), 2)
        self.assertEqual(entradas[0]['changed_by'], 'B')


class PermisosTests(TestCase):
    def test_todos_los_permisos_concedidos_sin_autenticacion(self):
        permisos_otorgados = permisos.permisos_del_usuario(request=None)
        for permiso in permisos.TODOS_LOS_PERMISOS:
            self.assertTrue(permisos_otorgados[permiso])

    def test_endpoint_respeta_el_punto_unico_de_verificacion(self):
        """Si el punto único de verificación deniega un permiso, el endpoint debe rechazar la
        solicitud — prueba que la protección es real y no un 200 hardcodeado."""
        client = APIClient()
        with mock.patch('cartera.permisos.tiene_permiso', return_value=False):
            resp = client.put('/api/dashboards/cartera/layout', data=json.dumps({'version': 1, 'components': []}), content_type='application/json')
        self.assertEqual(resp.status_code, 403)

        with mock.patch('cartera.permisos.tiene_permiso', return_value=False):
            resp = client.post('/api/dashboards/cartera/layout/reset', data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp.status_code, 403)

        with mock.patch('cartera.permisos.tiene_permiso', return_value=False):
            resp = client.get('/api/dashboards/cartera/layout')
        self.assertEqual(resp.status_code, 403)
