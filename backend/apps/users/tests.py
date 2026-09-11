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

    def test_set_superuser_otorga_el_estado(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        usuario = User.objects.create_user(username='elena', email='elena@example.com', password='Clave-Segura-123')
        UserAdminService.set_superuser(usuario=usuario, es_superusuario=True, actor=admin)
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_superuser)

    def test_set_superuser_quita_el_estado_si_hay_otro_superusuario_activo(self):
        admin1 = User.objects.create_superuser(username='admin1', email='admin1@example.com', password='Clave-Segura-123')
        admin2 = User.objects.create_superuser(username='admin2', email='admin2@example.com', password='Clave-Segura-123')
        UserAdminService.set_superuser(usuario=admin2, es_superusuario=False, actor=admin1)
        admin2.refresh_from_db()
        self.assertFalse(admin2.is_superuser)

    def test_no_permite_quitar_el_estado_al_ultimo_superusuario_activo(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        with self.assertRaises(CarteraError):
            UserAdminService.set_superuser(usuario=admin, es_superusuario=False, actor=admin)
        admin.refresh_from_db()
        self.assertTrue(admin.is_superuser)

    def test_reset_password_cambia_la_contrasena_y_fuerza_su_cambio(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        usuario = User.objects.create_user(username='gaby', email='gaby@example.com', password='Clave-Vieja-123')
        _, password_temporal = UserAdminService.reset_password(usuario=usuario, actor=admin)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password(password_temporal))
        self.assertFalse(usuario.check_password('Clave-Vieja-123'))
        self.assertTrue(usuario.must_change_password)

    def test_reset_password_revoca_las_sesiones_activas(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        usuario = User.objects.create_user(username='hilda', email='hilda@example.com', password='Clave-Segura-123')
        sesion = Session.objects.create(user=usuario, refresh_token_jti='jti-2', expires_at=timezone.now() + timezone.timedelta(days=7))
        UserAdminService.reset_password(usuario=usuario, actor=admin)
        sesion.refresh_from_db()
        self.assertIsNotNone(sesion.revoked_at)

    def test_reset_password_registra_auditoria(self):
        from apps.audit.models import AuditEvent
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        usuario = User.objects.create_user(username='ivan', email='ivan@example.com', password='Clave-Segura-123')
        UserAdminService.reset_password(usuario=usuario, actor=admin)
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_PASSWORD_RESET_BY_ADMIN',
            actor=admin, entity_id=str(usuario.id),
        ).exists())

    def test_set_superuser_registra_auditoria(self):
        from apps.audit.models import AuditEvent
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        usuario = User.objects.create_user(username='fabian', email='fabian@example.com', password='Clave-Segura-123')
        UserAdminService.set_superuser(usuario=usuario, es_superusuario=True, actor=admin)
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_SUPERUSER_CHANGED',
            actor=admin, entity_id=str(usuario.id),
        ).exists())


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

    def test_restablecer_password_via_api(self):
        usuario = User.objects.create_user(username='julia', email='julia@example.com', password='Clave-Vieja-123')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f'/api/users/{usuario.id}/reset_password/')
        self.assertEqual(resp.status_code, 200)
        password_temporal = resp.json()['temporary_password']
        self.assertTrue(password_temporal)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password(password_temporal))
        self.assertTrue(resp.json()['must_change_password'])

    def test_restablecer_password_requiere_permiso(self):
        from django.contrib.auth.models import Permission
        usuario = User.objects.create_user(username='karla', email='karla@example.com', password='Clave-Segura-123')
        objetivo = User.objects.create_user(username='luis', email='luis@example.com', password='Clave-Segura-123')
        permiso = Permission.objects.get(codename='usuarios.editar', content_type__app_label='permissions')
        usuario.user_permissions.add(permiso)
        self.client.force_authenticate(user=usuario)

        resp = self.client.post(f'/api/users/{objetivo.id}/reset_password/')

        self.assertEqual(resp.status_code, 403)

    def test_un_superusuario_puede_otorgar_superusuario_a_otro(self):
        usuario = User.objects.create_user(username='gina', email='gina@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f'/api/users/{usuario.id}/superuser/', {'is_superuser': True}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['is_superuser'])
        usuario.refresh_from_db()
        self.assertTrue(usuario.is_superuser)

    def test_un_usuario_sin_superusuario_no_puede_otorgar_superusuario_aunque_tenga_usuarios_editar(self):
        from django.contrib.auth.models import Permission
        usuario = User.objects.create_user(username='hugo', email='hugo@example.com', password='Clave-Segura-123')
        objetivo = User.objects.create_user(username='ines', email='ines@example.com', password='Clave-Segura-123')
        permiso = Permission.objects.get(codename='usuarios.editar', content_type__app_label='permissions')
        usuario.user_permissions.add(permiso)
        self.client.force_authenticate(user=usuario)

        resp = self.client.post(f'/api/users/{objetivo.id}/superuser/', {'is_superuser': True}, format='json')

        self.assertEqual(resp.status_code, 403)
        objetivo.refresh_from_db()
        self.assertFalse(objetivo.is_superuser)

    def test_no_permite_quitar_superusuario_al_ultimo_activo_via_api(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f'/api/users/{self.admin.id}/superuser/', {'is_superuser': False}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'ULTIMO_ADMINISTRADOR_ACTIVO')

    def test_sin_sesiones_ultima_conexion_es_nula(self):
        User.objects.create_user(username='nina', email='nina@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/users/')
        fila = next(u for u in resp.json()['results'] if u['username'] == 'nina')
        self.assertIsNone(fila['ultima_conexion'])
        self.assertIsNone(fila['last_login'])

    def test_ultima_conexion_es_la_sesion_mas_reciente_no_la_primera(self):
        usuario = User.objects.create_user(username='oscar', email='oscar@example.com', password='Clave-Segura-123')
        vieja = timezone.now() - timezone.timedelta(days=5)
        nueva = timezone.now() - timezone.timedelta(hours=1)
        sesion_vieja = Session.objects.create(user=usuario, refresh_token_jti='jti-vieja', expires_at=timezone.now() + timezone.timedelta(days=7))
        Session.objects.filter(pk=sesion_vieja.pk).update(created_at=vieja)
        sesion_nueva = Session.objects.create(user=usuario, refresh_token_jti='jti-nueva', expires_at=timezone.now() + timezone.timedelta(days=7))
        Session.objects.filter(pk=sesion_nueva.pk).update(created_at=nueva)

        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/users/')
        fila = next(u for u in resp.json()['results'] if u['username'] == 'oscar')

        # Comparación por instante, con tolerancia de redondeo de la columna en SQL Server (no
        # por string exacto: la representación — offset local vs `Z`/UTC — depende de
        # `settings.TIME_ZONE`, no es lo que este test quiere probar).
        from django.utils.dateparse import parse_datetime
        devuelto = parse_datetime(fila['ultima_conexion'])
        self.assertLess(abs((devuelto - nueva).total_seconds()), 1)
        self.assertGreater(abs((devuelto - vieja).total_seconds()), 1)

    def test_ultima_conexion_de_una_sesion_ya_revocada_se_sigue_mostrando(self):
        usuario = User.objects.create_user(username='paola', email='paola@example.com', password='Clave-Segura-123')
        sesion = Session.objects.create(user=usuario, refresh_token_jti='jti-revocada', expires_at=timezone.now() + timezone.timedelta(days=7))
        sesion.revoke()

        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/users/')
        fila = next(u for u in resp.json()['results'] if u['username'] == 'paola')

        self.assertIsNotNone(fila['ultima_conexion'])

    def test_ultima_conexion_se_incluye_en_el_detalle_de_un_usuario(self):
        usuario = User.objects.create_user(username='quique', email='quique@example.com', password='Clave-Segura-123')
        Session.objects.create(user=usuario, refresh_token_jti='jti-detalle', expires_at=timezone.now() + timezone.timedelta(days=7))
        self.client.force_authenticate(user=self.admin)

        resp = self.client.get(f'/api/users/{usuario.id}/')

        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()['ultima_conexion'])


class EscaladaDePrivilegiosTests(TestCase):
    """Cierre de las rutas por las que un permiso asignable alcanzaba para llegar al control total.

    Cada test corresponde a un hallazgo de la revisión de seguridad: SEC-01 (auto-otorgamiento de
    permisos), SEC-02 (toma de la cuenta superusuario vía reset de contraseña o cambio de correo).
    """

    def setUp(self):
        self.client = APIClient()
        self.superusuario = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='Clave-Segura-123',
        )
        # Operador con `usuarios.editar` y `usuarios.restablecer_password`, sin ser superusuario:
        # el perfil exacto al que estaban expuestas las escaladas.
        self.operador = User.objects.create_user(
            username='operador', email='op@example.com', password='Clave-Segura-123',
        )
        for codename in ('usuarios.ver', 'usuarios.editar', 'usuarios.restablecer_password', 'usuarios.deshabilitar'):
            self.operador.user_permissions.add(
                Permission.objects.get(codename=codename, content_type__app_label='permissions'),
            )
        self.otro = User.objects.create_user(username='otro', email='otro@example.com', password='Clave-Segura-123')

    # --- SEC-01 -----------------------------------------------------------------------------
    def test_no_puede_asignarse_permisos_a_si_mismo(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(
            f'/api/users/{self.operador.id}/permissions/',
            {'codenames': ['auditoria.ver', 'configuracion.editar']}, format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'AUTO_MODIFICACION_NO_PERMITIDA')
        self.assertEqual(self.operador.user_permissions.filter(codename='auditoria.ver').count(), 0)

    def test_no_puede_asignarse_roles_a_si_mismo(self):
        rol = Group.objects.create(name='PODEROSO')
        rol.permissions.add(Permission.objects.get(codename='auditoria.ver', content_type__app_label='permissions'))
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(f'/api/users/{self.operador.id}/roles/', {'role_ids': [rol.id]}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'AUTO_MODIFICACION_NO_PERMITIDA')
        self.assertFalse(self.operador.groups.exists())

    def test_no_puede_otorgar_a_otro_un_permiso_que_no_tiene(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(
            f'/api/users/{self.otro.id}/permissions/', {'codenames': ['auditoria.ver']}, format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'PERMISO_NO_DELEGABLE')
        self.assertIn('auditoria.ver', resp.json()['detalles']['codenames'])
        self.assertFalse(self.otro.user_permissions.exists())

    def test_si_puede_otorgar_a_otro_un_permiso_que_si_tiene(self):
        """La delegación sigue funcionando — lo que se corta es otorgar más de lo propio."""
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(
            f'/api/users/{self.otro.id}/permissions/', {'codenames': ['usuarios.ver']}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(self.otro.user_permissions.filter(codename='usuarios.ver').exists())

    def test_un_superusuario_puede_otorgar_todo_el_catalogo(self):
        self.client.force_authenticate(user=self.superusuario)
        resp = self.client.post(
            f'/api/users/{self.otro.id}/permissions/',
            {'codenames': ['auditoria.ver', 'configuracion.editar']}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.otro.user_permissions.count(), 2)

    # --- SEC-02 -----------------------------------------------------------------------------
    def test_no_puede_restablecer_la_contrasena_de_un_superusuario(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(f'/api/users/{self.superusuario.id}/reset_password/', {}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'OBJETIVO_SUPERUSUARIO')
        self.assertNotIn('temporary_password', resp.json())
        self.superusuario.refresh_from_db()
        self.assertTrue(self.superusuario.check_password('Clave-Segura-123'))

    def test_no_puede_cambiar_el_correo_de_un_superusuario(self):
        """El correo gobierna la recuperación de contraseña: apuntarlo al buzón propio era la
        misma toma de control que el reset, por otra puerta."""
        self.client.force_authenticate(user=self.operador)
        resp = self.client.patch(
            f'/api/users/{self.superusuario.id}/', {'email': 'atacante@example.com'}, format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'OBJETIVO_SUPERUSUARIO')
        self.superusuario.refresh_from_db()
        self.assertEqual(self.superusuario.email, 'admin@example.com')

    def test_no_puede_deshabilitar_ni_bloquear_a_un_superusuario(self):
        self.client.force_authenticate(user=self.operador)
        for accion in ('disable', 'block'):
            resp = self.client.post(f'/api/users/{self.superusuario.id}/{accion}/', {}, format='json')
            self.assertEqual(resp.json()['error'], 'OBJETIVO_SUPERUSUARIO', accion)
        self.superusuario.refresh_from_db()
        self.assertEqual(self.superusuario.status, User.Status.ACTIVE)

    def test_un_superusuario_si_puede_restablecer_la_contrasena_de_otro_superusuario(self):
        otro_admin = User.objects.create_superuser(
            username='admin2', email='admin2@example.com', password='Clave-Segura-123',
        )
        self.client.force_authenticate(user=self.superusuario)
        resp = self.client.post(f'/api/users/{otro_admin.id}/reset_password/', {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('temporary_password', resp.json())

    def test_sigue_pudiendo_restablecer_la_contrasena_de_un_usuario_normal(self):
        self.client.force_authenticate(user=self.operador)
        resp = self.client.post(f'/api/users/{self.otro.id}/reset_password/', {}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('temporary_password', resp.json())
