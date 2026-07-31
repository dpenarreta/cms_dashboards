"""Creación de dashboards por área (contenedor únicamente, sin procesamiento de datos propio)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent
from cartera.exceptions import CarteraError
from cartera.models import Dashboard
from cartera.services.dashboards import crear_dashboard

User = get_user_model()


class CrearDashboardServiceTests(TestCase):
    def test_crea_el_dashboard_con_un_id_generado_a_partir_del_nombre(self):
        dashboard = crear_dashboard(nombre='Finanzas', area='Finanzas')
        self.assertEqual(dashboard.dashboard_id, 'finanzas')
        self.assertEqual(dashboard.name, 'Finanzas')

    def test_nombre_repetido_genera_un_id_unico(self):
        crear_dashboard(nombre='Logística')
        segundo = crear_dashboard(nombre='Logística')
        self.assertEqual(segundo.dashboard_id, 'logistica-2')

    def test_nombre_vacio_es_rechazado(self):
        with self.assertRaises(CarteraError) as ctx:
            crear_dashboard(nombre='   ')
        self.assertEqual(ctx.exception.codigo, 'NOMBRE_REQUERIDO')

    def test_registra_auditoria(self):
        usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        crear_dashboard(nombre='Talento Humano', area='RRHH', creado_por=usuario)
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_CREATED',
            actor=usuario, dashboard_id='talento-humano',
        ).exists())


class DashboardCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_sin_permiso_devuelve_403(self):
        usuario = User.objects.create_user(username='sin_permiso', email='sp@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        resp = self.client.post('/api/dashboards/', {'name': 'Comercial'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_con_permiso_crea_el_dashboard_y_aparece_en_autorizados(self):
        usuario = User.objects.create_user(username='con_permiso', email='cp@example.com', password='Clave-Segura-123')
        usuario.user_permissions.add(
            Permission.objects.get(codename='dashboard.crear', content_type__app_label='permissions'),
            Permission.objects.get(codename='dashboard.view', content_type__app_label='permissions'),
        )
        self.client.force_authenticate(user=usuario)

        resp = self.client.post('/api/dashboards/', {'name': 'Comercial', 'area': 'Ventas'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['dashboard_id'], 'comercial')
        self.assertTrue(Dashboard.objects.filter(dashboard_id='comercial').exists())

        listado = self.client.get('/api/dashboards/authorized')
        ids = [d['dashboard_id'] for d in listado.json()]
        self.assertIn('comercial', ids)

    def test_nombre_vacio_devuelve_400(self):
        usuario = User.objects.create_user(username='con_permiso2', email='cp2@example.com', password='Clave-Segura-123')
        usuario.user_permissions.add(Permission.objects.get(codename='dashboard.crear', content_type__app_label='permissions'))
        self.client.force_authenticate(user=usuario)
        resp = self.client.post('/api/dashboards/', {'name': ''}, format='json')
        self.assertEqual(resp.status_code, 400)
