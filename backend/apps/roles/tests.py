from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent

User = get_user_model()


class SiembraAdministradorGeneralTests(TestCase):
    def test_rol_administrador_general_tiene_el_catalogo_completo(self):
        from apps.permissions.catalog import PERMISSION_CATALOG
        grupo = Group.objects.get(name='ADMINISTRADOR_GENERAL')
        codenames = set(grupo.permissions.filter(content_type__app_label='permissions').values_list('codename', flat=True))
        self.assertEqual(codenames, {p['codename'] for p in PERMISSION_CATALOG})

    def test_usuario_en_el_grupo_hereda_todos_los_permisos(self):
        from apps.permissions.authorization import user_has_permission
        usuario = User.objects.create_user(username='gerente', email='gerente@example.com', password='Clave-Segura-123')
        usuario.groups.add(Group.objects.get(name='ADMINISTRADOR_GENERAL'))
        self.assertTrue(user_has_permission(usuario, 'dashboard.configuration.reset'))
        self.assertTrue(user_has_permission(usuario, 'usuarios.crear'))


class RoleViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')

    def test_listar_roles_requiere_permiso(self):
        usuario = User.objects.create_user(username='sin_permiso', email='sp@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        resp = self.client.get('/api/roles/')
        self.assertEqual(resp.status_code, 403)

    def test_administrador_general_puede_crear_rol_con_permisos(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/roles/', {
            'name': 'Cobranzas', 'permission_codenames': ['dashboard.view', 'dashboard.edit'],
        }, format='json')
        self.assertEqual(resp.status_code, 201)
        rol = Group.objects.get(name='Cobranzas')
        self.assertEqual(
            set(rol.permissions.filter(content_type__app_label='permissions').values_list('codename', flat=True)),
            {'dashboard.view', 'dashboard.edit'},
        )

    def test_rechaza_permiso_no_reconocido(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post('/api/roles/', {'name': 'Invalido', 'permission_codenames': ['no.existe']}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_rechaza_nombre_de_rol_duplicado(self):
        self.client.force_authenticate(user=self.admin)
        Group.objects.create(name='Cobranzas')
        resp = self.client.post('/api/roles/', {'name': 'Cobranzas', 'permission_codenames': []}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_eliminar_rol(self):
        self.client.force_authenticate(user=self.admin)
        rol = Group.objects.create(name='Temporal')
        resp = self.client.delete(f'/api/roles/{rol.id}/')
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Group.objects.filter(id=rol.id).exists())

    def test_crear_rol_registra_auditoria(self):
        self.client.force_authenticate(user=self.admin)
        self.client.post('/api/roles/', {'name': 'Cobranzas', 'permission_codenames': ['dashboard.view']}, format='json')
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.ROLE_MANAGEMENT, action='ROLE_CREATED', entity_name='Cobranzas',
        ).exists())

    def test_modificar_permisos_de_un_rol_registra_auditoria(self):
        """AC-INT-013 (tests/qa/skelleton_base_integration.feature): un administrador que
        modifica los permisos de un rol debe quedar registrado en la auditoría."""
        self.client.force_authenticate(user=self.admin)
        rol = Group.objects.create(name='Cobranzas')

        resp = self.client.patch(f'/api/roles/{rol.id}/', {'permission_codenames': ['dashboard.view', 'roles.ver']}, format='json')

        self.assertEqual(resp.status_code, 200)
        entrada = AuditEvent.objects.filter(
            domain=AuditEvent.Domain.ROLE_MANAGEMENT, action='ROLE_UPDATED', entity_id=str(rol.id),
        ).first()
        self.assertIsNotNone(entrada)
        self.assertEqual(entrada.actor_id, self.admin.id)

    def test_catalogo_de_permisos_disponible_para_armar_el_formulario_de_rol(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/roles/permissions-catalog/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('dashboard', resp.json()['modules'])
