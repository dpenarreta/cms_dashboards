"""Edición (nombre/área) y eliminación (con confirmación de nombre) de dashboards por área."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from cartera.exceptions import CarteraError
from cartera.models import CargaArchivo, Dashboard
from cartera.services.dashboards import actualizar_dashboard, crear_dashboard, eliminar_dashboard

User = get_user_model()


class ActualizarDashboardServiceTests(TestCase):
    def test_actualiza_nombre_y_area(self):
        dashboard = crear_dashboard(nombre='Finanzas', area='Finanzas')
        actualizado = actualizar_dashboard(dashboard.dashboard_id, nombre='Finanzas y Contabilidad', area='FyC')
        self.assertEqual(actualizado.name, 'Finanzas y Contabilidad')
        self.assertEqual(actualizado.area, 'FyC')
        # El dashboard_id (slug) no cambia al editar, solo nombre/área.
        self.assertEqual(actualizado.dashboard_id, 'finanzas')

    def test_dashboard_inexistente_es_rechazado(self):
        with self.assertRaises(CarteraError) as ctx:
            actualizar_dashboard('no-existe', nombre='X')
        self.assertEqual(ctx.exception.codigo, 'DASHBOARD_NO_ENCONTRADO')

    def test_nombre_vacio_es_rechazado(self):
        dashboard = crear_dashboard(nombre='Logística')
        with self.assertRaises(CarteraError) as ctx:
            actualizar_dashboard(dashboard.dashboard_id, nombre='   ')
        self.assertEqual(ctx.exception.codigo, 'NOMBRE_REQUERIDO')

    def test_registra_auditoria_con_valores_anteriores_y_nuevos(self):
        usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        dashboard = crear_dashboard(nombre='Talento Humano', area='RRHH')
        actualizar_dashboard(dashboard.dashboard_id, nombre='Talento Humano y Nómina', area='RRHH', actor=usuario)
        evento = AuditEvent.objects.get(
            domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_UPDATED', dashboard_id=dashboard.dashboard_id,
        )
        self.assertEqual(evento.previous_values, {'name': 'Talento Humano', 'area': 'RRHH'})
        self.assertEqual(evento.new_values, {'name': 'Talento Humano y Nómina', 'area': 'RRHH'})
        self.assertEqual(evento.actor, usuario)


class EliminarDashboardServiceTests(TestCase):
    def test_elimina_con_confirmacion_correcta(self):
        dashboard = crear_dashboard(nombre='Comercial')
        eliminar_dashboard(dashboard.dashboard_id, confirmacion_nombre='Comercial')
        self.assertFalse(Dashboard.objects.filter(dashboard_id='comercial').exists())

    def test_confirmacion_incorrecta_no_elimina(self):
        dashboard = crear_dashboard(nombre='Comercial')
        with self.assertRaises(CarteraError) as ctx:
            eliminar_dashboard(dashboard.dashboard_id, confirmacion_nombre='comercial mal escrito')
        self.assertEqual(ctx.exception.codigo, 'CONFIRMACION_INVALIDA')
        self.assertTrue(Dashboard.objects.filter(dashboard_id='comercial').exists())

    def test_elimina_tambien_las_cargas_de_archivo_asociadas(self):
        dashboard = crear_dashboard(nombre='Comercial')
        CargaArchivo.objects.create(dashboard_id=dashboard.dashboard_id, nombre_original='datos.xlsx')
        eliminar_dashboard(dashboard.dashboard_id, confirmacion_nombre='Comercial')
        self.assertFalse(CargaArchivo.objects.filter(dashboard_id='comercial').exists())

    def test_registra_auditoria_con_los_valores_eliminados(self):
        usuario = User.objects.create_user(username='ana2', email='ana2@example.com', password='Clave-Segura-123')
        dashboard = crear_dashboard(nombre='Logística', area='Operaciones')
        eliminar_dashboard(dashboard.dashboard_id, confirmacion_nombre='Logística', actor=usuario)
        evento = AuditEvent.objects.get(
            domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_DELETED', dashboard_id='logistica',
        )
        self.assertEqual(evento.previous_values, {'name': 'Logística', 'area': 'Operaciones'})
        self.assertEqual(evento.actor, usuario)


class DashboardDetailViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _usuario_con(self, *codenames, username):
        usuario = User.objects.create_user(username=username, email=f'{username}@example.com', password='Clave-Segura-123')
        for codename in codenames:
            usuario.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label='permissions'))
        return usuario

    def test_patch_sin_permiso_devuelve_403(self):
        dashboard = crear_dashboard(nombre='Ventas')
        usuario = self._usuario_con(username='sin_editar')
        self.client.force_authenticate(user=usuario)
        resp = self.client.patch(f'/api/dashboards/{dashboard.dashboard_id}/', {'name': 'Ventas Nacionales'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_patch_con_permiso_actualiza(self):
        dashboard = crear_dashboard(nombre='Ventas')
        usuario = self._usuario_con('dashboard.editar', username='con_editar')
        self.client.force_authenticate(user=usuario)
        resp = self.client.patch(f'/api/dashboards/{dashboard.dashboard_id}/', {'name': 'Ventas Nacionales', 'area': 'Comercial'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['name'], 'Ventas Nacionales')
        dashboard.refresh_from_db()
        self.assertEqual(dashboard.name, 'Ventas Nacionales')

    def test_delete_sin_permiso_devuelve_403(self):
        dashboard = crear_dashboard(nombre='Ventas')
        usuario = self._usuario_con(username='sin_eliminar')
        self.client.force_authenticate(user=usuario)
        resp = self.client.delete(f'/api/dashboards/{dashboard.dashboard_id}/', {'confirmation_name': 'Ventas'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_delete_con_permiso_y_confirmacion_correcta_elimina(self):
        dashboard = crear_dashboard(nombre='Ventas')
        usuario = self._usuario_con('dashboard.eliminar', username='con_eliminar')
        self.client.force_authenticate(user=usuario)
        resp = self.client.delete(f'/api/dashboards/{dashboard.dashboard_id}/', {'confirmation_name': 'Ventas'}, format='json')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Dashboard.objects.filter(dashboard_id='ventas').exists())

    def test_delete_con_confirmacion_incorrecta_devuelve_400(self):
        dashboard = crear_dashboard(nombre='Ventas')
        usuario = self._usuario_con('dashboard.eliminar', username='con_eliminar2')
        self.client.force_authenticate(user=usuario)
        resp = self.client.delete(f'/api/dashboards/{dashboard.dashboard_id}/', {'confirmation_name': 'otro nombre'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(Dashboard.objects.filter(dashboard_id='ventas').exists())
