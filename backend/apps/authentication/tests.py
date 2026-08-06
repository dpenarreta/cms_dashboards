import io
import os
import tempfile

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import serializers as drf_serializers
from rest_framework.test import APIClient

from apps.audit.models import AuditEvent

from .models import LoginAttempt, PasswordResetToken, Session
from .serializers import AvatarUploadSerializer
from .services import MENSAJE_GENERICO_RECUPERACION, PasswordResetService, _hash_token

User = get_user_model()


def _imagen_de_prueba(nombre='avatar.png', color=(255, 0, 0)):
    buffer = io.BytesIO()
    Image.new('RGB', (10, 10), color).save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile(nombre, buffer.read(), content_type='image/png')


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')

    def test_login_valido_devuelve_tokens(self):
        resp = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.json())
        self.assertIn('refresh', resp.json())
        self.assertTrue(Session.objects.filter(user=self.usuario).exists())

    def test_login_con_email_tambien_funciona(self):
        resp = self.client.post('/api/auth/login', {'identifier': 'ana@example.com', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_login_invalido_no_revela_si_el_usuario_existe(self):
        resp1 = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'incorrecta'}, format='json')
        resp2 = self.client.post('/api/auth/login', {'identifier': 'no-existe', 'password': 'incorrecta'}, format='json')
        self.assertEqual(resp1.status_code, 400)
        self.assertEqual(resp2.status_code, 400)
        self.assertEqual(resp1.json()['error'], 'CREDENCIALES_INVALIDAS')
        self.assertEqual(resp2.json()['error'], 'CREDENCIALES_INVALIDAS')

    def test_usuario_deshabilitado_no_puede_loguearse(self):
        self.usuario.status = User.Status.DISABLED
        self.usuario.save()
        resp = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.status_code, 400)

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3)
    def test_bloqueo_por_fuerza_bruta(self):
        for _ in range(3):
            self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'incorrecta'}, format='json')
        resp = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'CUENTA_BLOQUEADA_TEMPORALMENTE')
        self.assertEqual(LoginAttempt.objects.filter(identifier='ana').count(), 3)


class RefreshLogoutMeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        login = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json').json()
        self.access, self.refresh = login['access'], login['refresh']

    def test_refresh_devuelve_nuevo_access(self):
        resp = self.client.post('/api/auth/token/refresh', {'refresh': self.refresh}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.json())

    def test_me_requiere_autenticacion(self):
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 401)

    def test_me_con_token_valido(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['username'], 'ana')

    def test_logout_revoca_la_sesion_y_el_access_deja_de_servir(self):
        resp = self.client.post('/api/auth/logout', {'refresh': self.refresh}, format='json')
        self.assertEqual(resp.status_code, 204)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access}')
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.status_code, 401)

    def test_refresh_reutilizado_tras_revocar_sesion_falla(self):
        self.client.post('/api/auth/logout', {'refresh': self.refresh}, format='json')
        resp = self.client.post('/api/auth/token/refresh', {'refresh': self.refresh}, format='json')
        self.assertEqual(resp.status_code, 400)


class SessionModelTests(TestCase):
    def test_sesion_expirada_no_esta_activa(self):
        usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        sesion = Session.objects.create(user=usuario, refresh_token_jti='jti-x', expires_at=timezone.now() - timezone.timedelta(days=1))
        self.assertFalse(sesion.is_active)

    def test_revoke_marca_revoked_at(self):
        usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        sesion = Session.objects.create(user=usuario, refresh_token_jti='jti-y', expires_at=timezone.now() + timezone.timedelta(days=1))
        sesion.revoke()
        self.assertIsNotNone(sesion.revoked_at)
        self.assertFalse(sesion.is_active)


class ChangeOwnPasswordViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Vieja-123', must_change_password=True)
        login = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Vieja-123'}, format='json').json()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login["access"]}')

    def test_cambio_de_contrasena_exitoso_limpia_must_change_password(self):
        resp = self.client.post('/api/auth/password/change', {'old_password': 'Clave-Vieja-123', 'new_password': 'Clave-Nueva-456'}, format='json')
        self.assertEqual(resp.status_code, 204)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.must_change_password)
        self.assertTrue(self.usuario.check_password('Clave-Nueva-456'))

    def test_contrasena_actual_incorrecta_es_rechazada(self):
        resp = self.client.post('/api/auth/password/change', {'old_password': 'incorrecta', 'new_password': 'Clave-Nueva-456'}, format='json')
        self.assertEqual(resp.status_code, 400)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MyProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        login = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json').json()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login["access"]}')

    def test_me_incluye_area_y_avatar_url_vacios_por_defecto(self):
        resp = self.client.get('/api/auth/me')
        self.assertEqual(resp.json()['area'], '')
        self.assertIsNone(resp.json()['avatar_url'])

    def test_actualizar_area_propia(self):
        resp = self.client.patch('/api/auth/me', {'area': 'Cobranzas'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['area'], 'Cobranzas')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.area, 'Cobranzas')

    def test_actualizar_area_registra_auditoria(self):
        self.client.patch('/api/auth/me', {'area': 'Cobranzas'}, format='json')
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_PROFILE_UPDATED',
            actor=self.usuario, entity_id=str(self.usuario.id),
        ).exists())

    def test_subir_avatar_exitoso(self):
        resp = self.client.post('/api/auth/me/avatar', {'avatar': _imagen_de_prueba()}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()['avatar_url'])
        self.usuario.refresh_from_db()
        self.assertTrue(bool(self.usuario.avatar))

    def test_subir_avatar_registra_auditoria(self):
        self.client.post('/api/auth/me/avatar', {'avatar': _imagen_de_prueba()}, format='multipart')
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_AVATAR_UPDATED', actor=self.usuario,
        ).exists())

    def test_subir_avatar_rechaza_archivo_que_no_es_imagen(self):
        archivo = SimpleUploadedFile('documento.txt', b'no es una imagen', content_type='text/plain')
        resp = self.client.post('/api/auth/me/avatar', {'avatar': archivo}, format='multipart')
        self.assertEqual(resp.status_code, 400)

    def test_subir_un_avatar_nuevo_borra_el_anterior_del_disco(self):
        self.client.post('/api/auth/me/avatar', {'avatar': _imagen_de_prueba()}, format='multipart')
        self.usuario.refresh_from_db()
        ruta_anterior = self.usuario.avatar.path
        self.assertTrue(os.path.exists(ruta_anterior))

        self.client.post('/api/auth/me/avatar', {'avatar': _imagen_de_prueba(color=(0, 255, 0))}, format='multipart')
        self.assertFalse(os.path.exists(ruta_anterior))

    def test_avatar_requiere_autenticacion(self):
        self.client.credentials()
        resp = self.client.post('/api/auth/me/avatar', {'avatar': _imagen_de_prueba()}, format='multipart')
        self.assertEqual(resp.status_code, 401)


class AvatarUploadSerializerTests(TestCase):
    def test_rechaza_archivo_mayor_a_2mb(self):
        archivo = _imagen_de_prueba()
        archivo.size = 3 * 1024 * 1024
        serializer = AvatarUploadSerializer()
        with self.assertRaises(drf_serializers.ValidationError):
            serializer.validate_avatar(archivo)


class PasswordResetServiceTests(TestCase):
    """13.4 del prompt. Django fuerza automáticamente `EMAIL_BACKEND` al backend en memoria
    (`locmem`) durante `TestCase` — nunca se envía un correo real aquí, sin importar lo que diga
    `settings.EMAIL_BACKEND`; los correos "enviados" quedan en `django.core.mail.outbox`."""

    def setUp(self):
        self.usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')

    def test_solicitud_valida_genera_token_y_envia_un_correo(self):
        mensaje = PasswordResetService.solicitar(email='ana@example.com')
        self.assertEqual(mensaje, MENSAJE_GENERICO_RECUPERACION)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.usuario).count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('ana@example.com', mail.outbox[0].to)
        self.assertEqual(mail.outbox[0].subject, 'Recuperación de contraseña | CMS Dashboards')

    def test_correo_no_registrado_devuelve_el_mismo_mensaje_generico_sin_enviar_correo(self):
        mensaje = PasswordResetService.solicitar(email='no-existe@example.com')
        self.assertEqual(mensaje, MENSAJE_GENERICO_RECUPERACION)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(PasswordResetToken.objects.count(), 0)

    def test_usuario_inactivo_no_recibe_correo_pero_el_mensaje_es_el_mismo(self):
        self.usuario.status = User.Status.DISABLED
        self.usuario.save()
        mensaje = PasswordResetService.solicitar(email='ana@example.com')
        self.assertEqual(mensaje, MENSAJE_GENERICO_RECUPERACION)
        self.assertEqual(len(mail.outbox), 0)

    def test_el_enlace_del_correo_usa_frontend_url_y_no_expone_el_token_hasheado(self):
        with override_settings(FRONTEND_URL='https://cms.ejemplo.org'):
            PasswordResetService.solicitar(email='ana@example.com')
        cuerpo = mail.outbox[0].body
        self.assertIn('https://cms.ejemplo.org/reset-password?token=', cuerpo)
        token = PasswordResetToken.objects.get(user=self.usuario)
        self.assertNotIn(token.token_hash, cuerpo)

    def test_una_nueva_solicitud_invalida_el_token_anterior(self):
        PasswordResetService.solicitar(email='ana@example.com')
        token_anterior = PasswordResetToken.objects.get(user=self.usuario)
        PasswordResetService.solicitar(email='ana@example.com')
        token_anterior.refresh_from_db()
        self.assertIsNotNone(token_anterior.used_at)
        self.assertEqual(PasswordResetToken.objects.filter(user=self.usuario, used_at__isnull=True).count(), 1)

    def _token_crudo_valido(self):
        raw = 'token-de-prueba-abc123'
        PasswordResetToken.objects.create(
            user=self.usuario, token_hash=_hash_token(raw),
            expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        return raw

    def test_token_valido_pasa_la_validacion(self):
        raw = self._token_crudo_valido()
        token = PasswordResetService.validar(raw_token=raw)
        self.assertEqual(token.user_id, self.usuario.id)

    def test_token_inexistente_es_rechazado(self):
        with self.assertRaises(Exception) as ctx:
            PasswordResetService.validar(raw_token='no-existe')
        self.assertEqual(ctx.exception.codigo, 'TOKEN_INVALIDO')

    def test_token_expirado_es_rechazado(self):
        raw = 'token-expirado-xyz'
        PasswordResetToken.objects.create(
            user=self.usuario, token_hash=_hash_token(raw),
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        with self.assertRaises(Exception) as ctx:
            PasswordResetService.validar(raw_token=raw)
        self.assertEqual(ctx.exception.codigo, 'TOKEN_EXPIRADO')

    def test_token_ya_usado_es_rechazado(self):
        raw = self._token_crudo_valido()
        PasswordResetService.confirmar(raw_token=raw, new_password='Clave-Nueva-789')
        with self.assertRaises(Exception) as ctx:
            PasswordResetService.validar(raw_token=raw)
        self.assertEqual(ctx.exception.codigo, 'TOKEN_INVALIDO')

    def test_cambio_exitoso_actualiza_password_invalida_token_y_revoca_sesiones(self):
        raw = self._token_crudo_valido()
        sesion = Session.objects.create(user=self.usuario, refresh_token_jti='jti-activa', expires_at=timezone.now() + timezone.timedelta(days=1))

        usuario = PasswordResetService.confirmar(raw_token=raw, new_password='Clave-Nueva-789')

        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('Clave-Nueva-789'))
        token = PasswordResetToken.objects.get(user=self.usuario)
        self.assertIsNotNone(token.used_at)
        sesion.refresh_from_db()
        self.assertFalse(sesion.is_active)
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_COMPLETED', actor=self.usuario,
        ).exists())


class PasswordResetApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Vieja-123')

    def test_solicitud_valida_devuelve_200_y_mensaje_generico(self):
        resp = self.client.post('/api/auth/password-reset/request', {'email': 'ana@example.com'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['message'], MENSAJE_GENERICO_RECUPERACION)

    def test_correo_no_registrado_devuelve_el_mismo_200_y_mensaje(self):
        resp = self.client.post('/api/auth/password-reset/request', {'email': 'nadie@example.com'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['message'], MENSAJE_GENERICO_RECUPERACION)

    def test_rate_limiting_bloquea_solicitudes_excesivas(self):
        from rest_framework.throttling import ScopedRateThrottle
        rates_originales = ScopedRateThrottle.THROTTLE_RATES
        ScopedRateThrottle.THROTTLE_RATES = {'password_reset': '2/hour'}
        self.addCleanup(setattr, ScopedRateThrottle, 'THROTTLE_RATES', rates_originales)
        self.addCleanup(ScopedRateThrottle.cache.clear)
        # Limpia también antes: pruebas anteriores de esta misma clase ya pegaron a este mismo
        # endpoint (misma IP de prueba) bajo la tasa por defecto — sin esto, esos hits previos
        # cuentan contra la tasa más estricta que fijamos aquí y el throttling dispara antes de
        # tiempo.
        ScopedRateThrottle.cache.clear()

        for _ in range(2):
            resp = self.client.post('/api/auth/password-reset/request', {'email': 'ana@example.com'}, format='json')
            self.assertEqual(resp.status_code, 200)
        resp = self.client.post('/api/auth/password-reset/request', {'email': 'ana@example.com'}, format='json')
        self.assertEqual(resp.status_code, 429)

    def test_confirmar_con_contrasenas_no_coincidentes_es_rechazado(self):
        raw = 'token-api-confirm'
        PasswordResetToken.objects.create(
            user=self.usuario, token_hash=_hash_token(raw), expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        resp = self.client.post('/api/auth/password-reset/confirm', {
            'token': raw, 'new_password': 'Clave-Nueva-789', 'confirm_password': 'Otra-Clave-000',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_confirmar_con_contrasena_debil_es_rechazado(self):
        raw = 'token-api-confirm-debil'
        PasswordResetToken.objects.create(
            user=self.usuario, token_hash=_hash_token(raw), expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        resp = self.client.post('/api/auth/password-reset/confirm', {
            'token': raw, 'new_password': '123', 'confirm_password': '123',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_confirmar_exitoso_permite_iniciar_sesion_con_la_nueva_contrasena(self):
        raw = 'token-api-confirm-ok'
        PasswordResetToken.objects.create(
            user=self.usuario, token_hash=_hash_token(raw), expires_at=timezone.now() + timezone.timedelta(minutes=30),
        )
        resp = self.client.post('/api/auth/password-reset/confirm', {
            'token': raw, 'new_password': 'Clave-Nueva-789', 'confirm_password': 'Clave-Nueva-789',
        }, format='json')
        self.assertEqual(resp.status_code, 200)

        login = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Nueva-789'}, format='json')
        self.assertEqual(login.status_code, 200)

    def test_validar_token_invalido_devuelve_400(self):
        resp = self.client.post('/api/auth/password-reset/validate', {'token': 'no-existe'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'TOKEN_INVALIDO')
