import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from cartera import permisos
from cartera.models import DashboardComponent, DashboardLayout
from cartera.services import dashboard_layout as dl

User = get_user_model()


def _cliente_autenticado():
    """Desde la Fase 5, todo endpoint de `cartera`/`dashboards` exige `IsAuthenticated` +
    `dashboard.*` — un superusuario bypasea la resolución de permisos por diseño
    (`apps.permissions.authorization.user_has_permission`)."""
    client = APIClient()
    usuario = User.objects.create_superuser(username=f'tester_{User.objects.count()}', email=f'tester{User.objects.count()}@example.com', password='Clave-Segura-123')
    client.force_authenticate(user=usuario)
    return client


def _generar_componentes(dashboard_id, cantidad=2):
    """Agrega `cantidad` componentes vía `agregar_componente_generado`, como si el usuario
    hubiese subido un archivo y confirmado esa cantidad de recomendaciones — fixture reutilizada
    por varios tests que necesitan un layout no vacío para editar."""
    layout = None
    for i in range(1, cantidad + 1):
        especificacion = {
            'titulo': f'Gráfica {i}', 'columna_valor': 'valor', 'columna_categoria': 'categoria',
            'datos': {'tipo': 'chart', 'categorias': ['A', 'B'], 'valores': [10.0, 20.0]},
        }
        layout = dl.agregar_componente_generado(dashboard_id, especificacion, reemplazar_existentes=(i == 1))
    return layout


class LayoutVacioTests(TestCase):
    def setUp(self):
        self.client = _cliente_autenticado()

    def test_un_dashboard_nuevo_no_tiene_componentes(self):
        """Ya no existe un layout fijo predefinido: un dashboard recién creado arranca sin
        componentes hasta que se genera un dashboard a partir de un archivo cargado."""
        resp = self.client.get('/api/dashboards/finanzas/layout')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['components'], [])
        self.assertTrue(DashboardLayout.objects.filter(dashboard_id='finanzas').exists())


class AgregarComponenteGeneradoTests(TestCase):
    def test_crea_un_componente_kpi(self):
        especificacion = {'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 100.0}}
        layout = dl.agregar_componente_generado('finanzas', especificacion)
        componentes = list(layout.components.all())
        self.assertEqual(len(componentes), 1)
        self.assertEqual(componentes[0].type, DashboardComponent.Tipo.KPI)
        self.assertEqual(componentes[0].content, {'titulo': 'Total', 'descripcion': '', 'valor': 100.0})

    def test_crea_un_componente_chart(self):
        especificacion = {
            'titulo': 'Por ciudad', 'columna_valor': 'saldo', 'columna_categoria': 'ciudad',
            'datos': {'tipo': 'chart', 'categorias': ['Quito'], 'valores': [100.0]},
        }
        layout = dl.agregar_componente_generado('finanzas', especificacion)
        componente = layout.components.get()
        self.assertEqual(componente.type, DashboardComponent.Tipo.CHART)
        self.assertEqual(componente.content['categorias'], ['Quito'])
        self.assertEqual(componente.content['valores'], [100.0])

    def test_agregar_sucesivamente_suma_componentes_en_vez_de_reemplazar(self):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Primera', 'columna_valor': 'x', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        layout = dl.agregar_componente_generado('finanzas', {
            'titulo': 'Segunda', 'columna_valor': 'y', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 2.0},
        })
        ids = sorted(c.component_id for c in layout.components.all())
        self.assertEqual(ids, ['primera', 'segunda'])

    def test_titulos_repetidos_generan_ids_unicos(self):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Ventas', 'columna_valor': 'x', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        layout = dl.agregar_componente_generado('finanzas', {
            'titulo': 'Ventas', 'columna_valor': 'y', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 2.0},
        })
        ids = sorted(c.component_id for c in layout.components.all())
        self.assertEqual(ids, ['ventas', 'ventas-2'])

    def test_reemplazar_existentes_empieza_de_cero(self):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Viejo', 'columna_valor': 'x', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        layout = dl.agregar_componente_generado('finanzas', {
            'titulo': 'Nuevo', 'columna_valor': 'y', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 2.0},
        }, reemplazar_existentes=True)
        ids = [c.component_id for c in layout.components.all()]
        self.assertEqual(ids, ['nuevo'])

    def test_registra_auditoria(self):
        usuario = User.objects.create_user(username='ana3', email='ana3@example.com', password='Clave-Segura-123')
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Ventas', 'columna_valor': 'x', 'columna_categoria': None, 'datos': {'tipo': 'kpi', 'valor': 1.0},
        }, actor=usuario)
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_CHART_ADDED',
            dashboard_id='finanzas', actor=usuario,
        ).exists())


class GuardarLayoutTests(TestCase):
    def setUp(self):
        self.client = _cliente_autenticado()
        _generar_componentes('finanzas', cantidad=2)
        self.data_inicial = self.client.get('/api/dashboards/finanzas/layout').json()

    def _guardar(self, componentes, version=None, changed_by='Tester'):
        payload = {'version': version if version is not None else self.data_inicial['version'], 'components': componentes, 'changed_by': changed_by}
        return self.client.put('/api/dashboards/finanzas/layout', data=json.dumps(payload), content_type='application/json')

    def test_guarda_cambio_de_orden_tamano_color_y_texto(self):
        comps = self.data_inicial['components']
        comps[0]['order'] = 10
        comps[1]['content']['titulo'] = 'Nuevo título'
        comps[1]['styles'] = {'colorPrincipal': '#123456'}
        comps[1]['width'] = 8

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['version'], self.data_inicial['version'] + 1)

        audit = list(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.DASHBOARD_LAYOUT, dashboard_id='finanzas',
        ).values_list('component_id', 'action'))
        self.assertIn((comps[0]['component_id'], dl.CambioLayout.ORDEN), audit)
        self.assertIn((comps[1]['component_id'], dl.CambioLayout.TEXTO), audit)
        self.assertIn((comps[1]['component_id'], dl.CambioLayout.COLOR), audit)
        self.assertIn((comps[1]['component_id'], dl.CambioLayout.TAMANO), audit)

    def test_ocultar_componente_registra_auditoria(self):
        comps = self.data_inicial['components']
        comps[0]['is_visible'] = False

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        oculto = next(c for c in resp.json()['components'] if c['component_id'] == comps[0]['component_id'])
        self.assertFalse(oculto['is_visible'])
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.DASHBOARD_LAYOUT,
            dashboard_id='finanzas', component_id=comps[0]['component_id'], action=dl.CambioLayout.OCULTADO,
        ).exists())

    def test_omitir_un_componente_lo_elimina_y_registra_auditoria(self):
        comps = self.data_inicial['components']
        eliminado_id = comps[0]['component_id']
        restantes = comps[1:]

        resp = self._guardar(restantes)
        self.assertEqual(resp.status_code, 200)
        ids_guardados = [c['component_id'] for c in resp.json()['components']]
        self.assertNotIn(eliminado_id, ids_guardados)
        self.assertEqual(len(ids_guardados), 1)

        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.DASHBOARD_LAYOUT,
            dashboard_id='finanzas', component_id=eliminado_id, action=dl.CambioLayout.ELIMINADO,
        ).exists())

    def test_eliminar_todos_los_componentes_deja_el_dashboard_vacio(self):
        resp = self._guardar([])
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['components'], [])

    def test_titulo_con_signo_mayor_que_no_se_corrompe(self):
        """Regresión: la sanitización no debe destruir texto legítimo como 'Ventas > 100'."""
        comps = self.data_inicial['components']
        comps[0]['content']['titulo'] = 'Ventas > 100'

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        guardado = next(c for c in resp.json()['components'] if c['component_id'] == comps[0]['component_id'])
        self.assertEqual(guardado['content']['titulo'], 'Ventas > 100')

    def test_sanitiza_etiquetas_html_del_titulo(self):
        comps = self.data_inicial['components']
        comps[0]['content']['titulo'] = '<script>alert(1)</script>Top clientes'

        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        guardado = next(c for c in resp.json()['components'] if c['component_id'] == comps[0]['component_id'])
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
        comps[0]['styles'] = {'colorPrincipal': 'javascript:alert(1)'}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLOR_INVALIDO')

    def test_acepta_color_hex_y_rgba(self):
        comps = self.data_inicial['components']
        comps[0]['styles'] = {'colorPrincipal': '#1F4E78', 'colorSecundario': 'rgba(198, 40, 40, 0.8)'}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)

    def test_acepta_un_color_distinto_por_categoria(self):
        comps = self.data_inicial['components']
        comps[0]['styles'] = {'coloresPorCategoria': {'Quito': '#1F4E78', 'Guayaquil': 'rgba(198, 40, 40, 0.8)'}}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        guardado = next(c for c in resp.json()['components'] if c['component_id'] == comps[0]['component_id'])
        self.assertEqual(guardado['styles']['coloresPorCategoria'], {'Quito': '#1F4E78', 'Guayaquil': 'rgba(198, 40, 40, 0.8)'})

    def test_rechaza_coloresPorCategoria_que_no_es_un_objeto(self):
        comps = self.data_inicial['components']
        comps[0]['styles'] = {'coloresPorCategoria': 'no-es-un-objeto'}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLOR_INVALIDO')

    def test_rechaza_un_color_invalido_dentro_de_coloresPorCategoria(self):
        comps = self.data_inicial['components']
        comps[0]['styles'] = {'coloresPorCategoria': {'Quito': 'javascript:alert(1)'}}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLOR_INVALIDO')

    def test_una_categoria_con_color_vacio_se_descarta_del_mapa(self):
        comps = self.data_inicial['components']
        comps[0]['styles'] = {'coloresPorCategoria': {'Quito': '#1F4E78', 'Guayaquil': ''}}
        resp = self._guardar(comps)
        self.assertEqual(resp.status_code, 200)
        guardado = next(c for c in resp.json()['components'] if c['component_id'] == comps[0]['component_id'])
        self.assertEqual(guardado['styles']['coloresPorCategoria'], {'Quito': '#1F4E78'})


class PaginacionEnComponenteTablaTests(TestCase):
    """`_sanitizar_config_paginacion` sigue vigente para cualquier componente tipo TABLE que
    exista en un layout (aunque el flujo de generación ya no cree ninguno por defecto)."""

    def setUp(self):
        self.client = _cliente_autenticado()
        layout = dl.obtener_o_crear_layout('finanzas')
        DashboardComponent.objects.create(
            layout=layout, component_id='tabla-detalle', type=DashboardComponent.Tipo.TABLE,
            row=1, order=1, width=12, height=400,
            content={'titulo': 'Detalle'}, config={'defaultPageSize': 10, 'allowedPageSizes': [5, 10, 25, 50, 100], 'paginationEnabled': True},
        )
        self.data_inicial = self.client.get('/api/dashboards/finanzas/layout').json()

    def test_page_size_por_defecto_invalido_cae_al_fallback(self):
        comps = self.data_inicial['components']
        comps[0]['config'] = {'defaultPageSize': 999, 'allowedPageSizes': [5, 10, 25, 50, 100]}
        resp = self.client.put(
            '/api/dashboards/finanzas/layout',
            data=json.dumps({'version': self.data_inicial['version'], 'components': comps}), content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        guardado = resp.json()['components'][0]
        self.assertEqual(guardado['config']['defaultPageSize'], 10)


class RestablecerLayoutTests(TestCase):
    def test_restablecer_vuelve_a_mostrar_los_componentes_ocultos(self):
        """'Restablecer' ya no regenera un layout fijo (no existe uno) — solo deshace los
        `is_visible=False` de los componentes que ya existen."""
        client = _cliente_autenticado()
        _generar_componentes('finanzas', cantidad=2)
        data = client.get('/api/dashboards/finanzas/layout').json()
        comps = data['components']
        comps[0]['is_visible'] = False
        client.put('/api/dashboards/finanzas/layout', data=json.dumps({'version': data['version'], 'components': comps}), content_type='application/json')

        resp = client.post('/api/dashboards/finanzas/layout/reset', data=json.dumps({'changed_by': 'Admin'}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        nuevo = resp.json()
        self.assertEqual(len(nuevo['components']), 2)
        antes_oculto = next(c for c in nuevo['components'] if c['component_id'] == comps[0]['component_id'])
        self.assertTrue(antes_oculto['is_visible'])
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION,
            dashboard_id='finanzas', action=dl.CambioLayout.RESTABLECIDO,
        ).exists())

    def test_versions_devuelve_historial_mas_reciente_primero(self):
        client = _cliente_autenticado()
        _generar_componentes('finanzas', cantidad=1)
        client.post('/api/dashboards/finanzas/layout/reset', data=json.dumps({'changed_by': 'A'}), content_type='application/json')
        client.post('/api/dashboards/finanzas/layout/reset', data=json.dumps({'changed_by': 'B'}), content_type='application/json')

        resp = client.get('/api/dashboards/finanzas/versions')
        entradas = resp.json()
        self.assertGreaterEqual(len(entradas), 2)
        self.assertEqual(entradas[0]['changed_by'], 'B')


class PermisosTests(TestCase):
    def test_sin_usuario_autenticado_no_se_concede_ningun_permiso(self):
        """Fase 5: se retiró el fallback histórico que concedía todo sin autenticación (fallo
        cerrado, no abierto — docs/integracion/decisions.md #6)."""
        permisos_otorgados = permisos.permisos_del_usuario(request=None)
        for permiso in permisos.TODOS_LOS_PERMISOS:
            self.assertFalse(permisos_otorgados[permiso])

    def test_endpoint_respeta_el_punto_unico_de_verificacion(self):
        """Si el punto único de verificación deniega un permiso, el endpoint debe rechazar la
        solicitud — prueba que la protección es real y no un 200 hardcodeado."""
        client = _cliente_autenticado()
        with mock.patch('cartera.permisos.tiene_permiso', return_value=False):
            resp = client.put('/api/dashboards/finanzas/layout', data=json.dumps({'version': 1, 'components': []}), content_type='application/json')
        self.assertEqual(resp.status_code, 403)

        with mock.patch('cartera.permisos.tiene_permiso', return_value=False):
            resp = client.post('/api/dashboards/finanzas/layout/reset', data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp.status_code, 403)

        with mock.patch('cartera.permisos.tiene_permiso', return_value=False):
            resp = client.get('/api/dashboards/finanzas/layout')
        self.assertEqual(resp.status_code, 403)
