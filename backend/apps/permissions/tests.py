from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .authorization import get_user_permission_codenames, user_has_permission
from .catalog import PERMISSION_CATALOG

User = get_user_model()


class CatalogoDePermisosTests(TestCase):
    def test_incluye_permisos_administrativos_y_de_dashboard(self):
        codenames = {p['codename'] for p in PERMISSION_CATALOG}
        self.assertIn('usuarios.ver', codenames)
        self.assertIn('roles.editar', codenames)
        self.assertIn('auditoria.exportar', codenames)
        self.assertIn('dashboard.view', codenames)
        self.assertIn('dashboard.configuration.reset', codenames)

    def test_endpoint_requiere_permiso_permisos_ver(self):
        client = APIClient()
        user = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        client.force_authenticate(user=user)
        resp = client.get('/api/permissions/')
        self.assertEqual(resp.status_code, 403)

    def test_administrador_general_puede_ver_el_catalogo(self):
        client = APIClient()
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        client.force_authenticate(user=admin)
        resp = client.get('/api/permissions/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('usuarios', resp.json()['modules'])


class AuthorizationHelpersTests(TestCase):
    def test_usuario_no_autenticado_no_tiene_permisos(self):
        self.assertEqual(get_user_permission_codenames(None), set())
        self.assertFalse(user_has_permission(None, 'usuarios.ver'))

    def test_superusuario_tiene_todos_los_permisos_del_catalogo(self):
        admin = User.objects.create_superuser(username='admin2', email='admin2@example.com', password='Clave-Segura-123')
        self.assertTrue(user_has_permission(admin, 'dashboard.configuration.reset'))
        self.assertEqual(get_user_permission_codenames(admin), {p['codename'] for p in PERMISSION_CATALOG})

    def test_usuario_normal_sin_permisos_asignados_no_tiene_ninguno(self):
        user = User.objects.create_user(username='bob', email='bob@example.com', password='Clave-Segura-123')
        self.assertFalse(user_has_permission(user, 'usuarios.ver'))
        self.assertEqual(get_user_permission_codenames(user), set())
