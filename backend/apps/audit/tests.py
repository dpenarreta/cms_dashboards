from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AuditEvent
from .services import log_event

User = get_user_model()


class LogEventTests(TestCase):
    def test_registra_un_evento_basico(self):
        evento = log_event(domain=AuditEvent.Domain.AUTHENTICATION, action='LOGIN_SUCCESS')
        self.assertIsNotNone(evento)
        self.assertEqual(evento.domain, AuditEvent.Domain.AUTHENTICATION)
        self.assertEqual(evento.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(evento.severity, AuditEvent.Severity.INFO)

    def test_severidad_por_defecto_segun_resultado(self):
        fallido = log_event(domain=AuditEvent.Domain.AUTHENTICATION, action='LOGIN_FAILED', result=AuditEvent.Result.FAILED)
        denegado = log_event(domain=AuditEvent.Domain.SECURITY, action='ACCESS_DENIED', result=AuditEvent.Result.DENIED)
        self.assertEqual(fallido.severity, AuditEvent.Severity.MEDIUM)
        self.assertEqual(denegado.severity, AuditEvent.Severity.MEDIUM)

    def test_severidad_explicita_tiene_prioridad(self):
        evento = log_event(domain=AuditEvent.Domain.SECURITY, action='X', result=AuditEvent.Result.FAILED, severity=AuditEvent.Severity.CRITICAL)
        self.assertEqual(evento.severity, AuditEvent.Severity.CRITICAL)

    def test_enmascara_valores_sensibles(self):
        evento = log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_CREATED',
            new_values={'username': 'ana', 'password': 'no-deberia-guardarse'},
        )
        self.assertEqual(evento.new_values['username'], 'ana')
        self.assertEqual(evento.new_values['password'], '***')

    def test_actor_anonimo_se_guarda_como_none(self):
        from django.contrib.auth.models import AnonymousUser
        evento = log_event(domain=AuditEvent.Domain.AUTHENTICATION, action='LOGIN_FAILED', actor=AnonymousUser())
        self.assertIsNone(evento.actor)

    def test_actor_autenticado_guarda_username(self):
        usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        evento = log_event(domain=AuditEvent.Domain.AUTHENTICATION, action='LOGIN_SUCCESS', actor=usuario)
        self.assertEqual(evento.actor_id, usuario.id)
        self.assertEqual(evento.actor_username, 'ana')

    def test_nunca_lanza_ante_un_dominio_invalido_para_choices(self):
        """`domain` fuera del catálogo de choices no rompe la operación que originó el evento.

        Lo que se verifica es el contrato de `log_event`: NUNCA lanza. Que además devuelva `None`
        depende del motor —SQL Server rechaza el valor por exceder `max_length` y la excepción se
        traga, SQLite no valida largo y la escritura pasa—, así que afirmarlo acoplaba la prueba a
        la base configurada y la hacía fallar con `DB_ENGINE=sqlite`.
        """
        demasiado_largo = 'NO_EXISTE_1234567890_MUY_LARGO_PARA_EL_CAMPO_QUE_DEBERIA_FALLAR_AL_VALIDAR_LONGITUD_MAXIMA_DEL_CAMPO'
        try:
            log_event(domain=demasiado_largo, action='X')
        except Exception as e:  # noqa: BLE001 - justamente lo que no debe pasar
            self.fail(f'log_event lanzó {type(e).__name__}: {e}')


class AuditEventApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')
        self.evento = log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_CREATED', actor=self.admin,
            entity_type='user', entity_id='7', previous_values={'a': 1}, new_values={'a': 2},
        )

    def test_listar_requiere_permiso_auditoria_ver(self):
        usuario = User.objects.create_user(username='sin_permiso', email='sp@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        resp = self.client.get('/api/audit/')
        self.assertEqual(resp.status_code, 403)

    def test_administrador_general_puede_listar(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/audit/')
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.json()['count'], 1)

    def test_filtrar_por_dominio(self):
        log_event(domain=AuditEvent.Domain.DASHBOARD_LAYOUT, action='COMPONENT_MOVED')
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/audit/', {'domain': 'DASHBOARD_LAYOUT'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(all(r['domain'] == 'DASHBOARD_LAYOUT' for r in resp.json()['results']))

    def test_detalle_incluye_valores_con_permiso_ver_detalle(self):
        usuario = User.objects.create_user(username='con_detalle', email='cd@example.com', password='Clave-Segura-123')
        for codename in ('auditoria.ver', 'auditoria.ver_detalle'):
            usuario.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label='permissions'))
        self.client.force_authenticate(user=usuario)
        resp = self.client.get(f'/api/audit/{self.evento.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('previous_values', resp.json())
        self.assertEqual(resp.json()['previous_values'], {'a': 1})

    def test_detalle_oculta_valores_sin_permiso_ver_detalle(self):
        usuario = User.objects.create_user(username='sin_detalle', email='sd@example.com', password='Clave-Segura-123')
        usuario.user_permissions.add(Permission.objects.get(codename='auditoria.ver', content_type__app_label='permissions'))
        self.client.force_authenticate(user=usuario)
        resp = self.client.get(f'/api/audit/{self.evento.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('previous_values', resp.json())
        self.assertNotIn('metadata', resp.json())

    def test_exportar_requiere_permiso_auditoria_exportar(self):
        usuario = User.objects.create_user(username='sin_export', email='se@example.com', password='Clave-Segura-123')
        usuario.user_permissions.add(Permission.objects.get(codename='auditoria.ver', content_type__app_label='permissions'))
        self.client.force_authenticate(user=usuario)
        resp = self.client.get('/api/audit/export/')
        self.assertEqual(resp.status_code, 403)

    def test_exportar_devuelve_csv(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/audit/export/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp['Content-Type'])
        self.assertIn(b'USER_CREATED', resp.content)
