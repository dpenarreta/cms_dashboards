from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import Session
from cartera.exceptions import CarteraError

from .models import User
from .services import UserAdminService


class UserModelTests(TestCase):
    def test_status_disabled_sincroniza_is_active_false(self):
        usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        self.assertTrue(usuario.is_active)
        usuario.status = User.Status.DISABLED
        usuario.save()
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_active)

    def test_email_unico(self):
        User.objects.create_user(username='ana', email='dup@example.com', password='Clave-Segura-123')
        with self.assertRaises(Exception):
            User.objects.create_user(username='otra', email='dup@example.com', password='Clave-Segura-123')


class UserAdminServiceTests(TestCase):
    def test_no_permite_deshabilitar_al_ultimo_administrador_activo(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        with self.assertRaises(CarteraError):
            UserAdminService.disable(usuario=admin, actor=admin)
        admin.refresh_from_db()
        self.assertEqual(admin.status, User.Status.ACTIVE)

    def test_permite_deshabilitar_admin_si_existe_otro_admin_activo(self):
        admin1 = User.objects.create_superuser(username='admin1', email='admin1@example.com', password='Clave-Segura-123')
        User.objects.create_superuser(username='admin2', email='admin2@example.com', password='Clave-Segura-123')
        UserAdminService.disable(usuario=admin1, actor=admin1)
        admin1.refresh_from_db()
        self.assertEqual(admin1.status, User.Status.DISABLED)

    def test_deshabilitar_usuario_revoca_sus_sesiones_activas(self):
        usuario = User.objects.create_user(username='bob', email='bob@example.com', password='Clave-Segura-123')
        sesion = Session.objects.create(user=usuario, refresh_token_jti='jti-1', expires_at=timezone.now() + timezone.timedelta(days=7))
        UserAdminService.disable(usuario=usuario, actor=usuario)
        sesion.refresh_from_db()
        self.assertIsNotNone(sesion.revoked_at)

    def test_assign_roles_reemplaza_los_roles_del_usuario(self):
        usuario = User.objects.create_user(username='carla', email='carla@example.com', password='Clave-Segura-123')
        rol = Group.objects.create(name='Consulta')
        UserAdminService.assign_roles(usuario=usuario, role_ids=[rol], actor=usuario)
        self.assertEqual(list(usuario.groups.values_list('name', flat=True)), ['Consulta'])

    def test_assign_permissions_por_codename_de_negocio(self):
        usuario = User.objects.create_user(username='dario', email='dario@example.com', password='Clave-Segura-123')
        permiso = Permission.objects.get(codename='dashboard.view', content_type__app_label='permissions')
        UserAdminService.assign_permissions(usuario=usuario, codenames=['dashboard.view'], actor=usuario)
        self.assertIn(permiso, usuario.user_permissions.all())


class UserAdminViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')

    def test_listar_usuarios_requiere_permiso(self):
        usuario = User.objects.create_user(username='sin_permiso', email='sp@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 403)

    def test_administrador_general_puede_listar_y_crear_usuarios(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/users/')
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post('/api/users/', {
            'username': 'nuevo', 'email': 'nuevo@example.com', 'password': 'Clave-Segura-123',
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username='nuevo').exists())

    def test_deshabilitar_usuario_via_api(self):
        usuario = User.objects.create_user(username='marcos', email='marcos@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f'/api/users/{usuario.id}/disable/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'disabled')

    def test_no_permite_eliminar_usuarios(self):
        usuario = User.objects.create_user(username='eli', email='eli@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.delete(f'/api/users/{usuario.id}/')
        self.assertEqual(resp.status_code, 405)
