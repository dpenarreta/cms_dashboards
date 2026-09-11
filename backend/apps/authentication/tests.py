import io
import os
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import serializers as drf_serializers
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from apps.audit.models import AuditEvent

from .models import EmailTemplate, LoginAttempt, PasswordResetToken, Session
from .serializers import AvatarUploadSerializer
from .services import MENSAJE_GENERICO_RECUPERACION, PasswordResetService, _hash_token, _renderizar_plantilla

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
        # Los intentos se cuentan contra un identificador canónico (`user:<pk>`), no contra el
        # texto tipeado — ver `BruteForceProtectionService.identificador_canonico`.
        usuario = User.objects.get(username='ana')
        self.assertEqual(LoginAttempt.objects.filter(identifier=f'user:{usuario.pk}').count(), 3)

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3)
    def test_alternar_usuario_y_correo_no_duplica_los_intentos_permitidos(self):
        """El bloqueo se aplica a la CUENTA, no al texto escrito.

        Antes se contaba el identificador crudo, así que `ana` y `ana@example.com` llevaban
        contadores separados: 3 intentos con uno y 3 más con el otro sobre la misma cuenta, sin
        bloqueo, y cada alias de correo sumaba otros 3.
        """
        for _ in range(2):
            self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'incorrecta'}, format='json')
        # El tercer fallo llega por el correo: mismo contador, así que alcanza el límite de 3.
        self.client.post('/api/auth/login', {'identifier': 'ana@example.com', 'password': 'incorrecta'}, format='json')

        resp = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.json()['error'], 'CUENTA_BLOQUEADA_TEMPORALMENTE')

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3)
    def test_variar_mayusculas_no_duplica_los_intentos_permitidos(self):
        """Mismo criterio que el test anterior, con la otra variante del agujero: la normalización
        no puede depender de que la colación de la base sea case-insensitive (lo es en SQL Server,
        no en SQLite)."""
        for _ in range(3):
            self.client.post('/api/auth/login', {'identifier': 'ANA', 'password': 'incorrecta'}, format='json')

        resp = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.json()['error'], 'CUENTA_BLOQUEADA_TEMPORALMENTE')

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3)
    def test_identificador_inexistente_tambien_acumula_y_bloquea(self):
        """Contar por identificador (y no solo por usuario resuelto) es lo que evita que enumerar
        cuentas sea gratis: un identificador que no existe también se bloquea."""
        for _ in range(3):
            self.client.post('/api/auth/login', {'identifier': 'no-existe', 'password': 'x'}, format='json')

        resp = self.client.post('/api/auth/login', {'identifier': 'no-existe', 'password': 'x'}, format='json')
        self.assertEqual(resp.json()['error'], 'CUENTA_BLOQUEADA_TEMPORALMENTE')
        self.assertEqual(LoginAttempt.objects.filter(identifier='no-existe').count(), 3)

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=100, LOGIN_MAX_FAILED_ATTEMPTS_PER_IP=3)
    def test_bloqueo_por_ip_ante_intentos_contra_muchas_cuentas_distintas(self):
        """El eje por cuenta no ve el rociado de una contraseña habitual contra muchas cuentas
        (cada cuenta recibe un único fallo), así que hay un umbral propio por IP."""
        for i in range(3):
            self.client.post('/api/auth/login', {'identifier': f'victima{i}', 'password': 'Verano2026'}, format='json')

        resp = self.client.post('/api/auth/login', {'identifier': 'otra-mas', 'password': 'Verano2026'}, format='json')
        self.assertEqual(resp.json()['error'], 'CUENTA_BLOQUEADA_TEMPORALMENTE')


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

    def test_actualizar_nombre_propio(self):
        resp = self.client.patch('/api/auth/me', {'first_name': 'Ana', 'last_name': 'Pérez'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['first_name'], 'Ana')
        self.assertEqual(resp.json()['last_name'], 'Pérez')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.first_name, 'Ana')
        self.assertEqual(self.usuario.last_name, 'Pérez')

    def test_actualizar_nombre_registra_auditoria_con_valores_previos(self):
        self.usuario.first_name = 'Nombre viejo'
        self.usuario.save(update_fields=['first_name'])
        self.client.patch('/api/auth/me', {'first_name': 'Ana'}, format='json')
        evento = AuditEvent.objects.get(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_PROFILE_UPDATED',
            actor=self.usuario, entity_id=str(self.usuario.id),
        )
        self.assertEqual(evento.previous_values, {'first_name': 'Nombre viejo'})
        self.assertEqual(evento.new_values, {'first_name': 'Ana'})

    def test_actualizar_nombre_con_mas_de_150_caracteres_es_rechazado(self):
        resp = self.client.patch('/api/auth/me', {'first_name': 'A' * 151}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_actualizar_username_propio(self):
        resp = self.client.patch('/api/auth/me', {'username': 'ana2'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['username'], 'ana2')
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.username, 'ana2')

    def test_actualizar_username_al_mismo_valor_no_falla_por_unicidad(self):
        resp = self.client.patch('/api/auth/me', {'username': 'ana'}, format='json')
        self.assertEqual(resp.status_code, 200)

    def test_actualizar_username_a_uno_ya_usado_por_otro_es_rechazado(self):
        User.objects.create_user(username='beto', email='beto@example.com', password='Clave-Segura-123')
        resp = self.client.patch('/api/auth/me', {'username': 'beto'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.username, 'ana')

    def test_actualizar_username_a_uno_ya_usado_es_rechazado_sin_importar_mayusculas(self):
        User.objects.create_user(username='beto', email='beto@example.com', password='Clave-Segura-123')
        resp = self.client.patch('/api/auth/me', {'username': 'BETO'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_actualizar_username_con_caracteres_invalidos_es_rechazado(self):
        resp = self.client.patch('/api/auth/me', {'username': 'ana con espacios'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_despues_de_cambiar_username_se_puede_iniciar_sesion_con_el_nuevo(self):
        self.client.patch('/api/auth/me', {'username': 'ana2'}, format='json')
        cliente_nuevo = APIClient()
        resp = cliente_nuevo.post('/api/auth/login', {'identifier': 'ana2', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.status_code, 200)

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
        self.assertEqual(mail.outbox[0].subject, 'Recuperación de contraseña | Dashboard de Cartera')

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


class RenderizarPlantillaTests(TestCase):
    """Sustitución propia de `{{ variable }}` (`services.py::_renderizar_plantilla`) — no el
    motor de templates de Django, ver el docstring de la función."""

    def test_sustituye_variables_conocidas(self):
        resultado = _renderizar_plantilla('Hola {{ nombre }}, tu enlace es {{ enlace }}.', {
            'nombre': 'Ana', 'enlace': 'https://x.test/y',
        })
        self.assertEqual(resultado, 'Hola Ana, tu enlace es https://x.test/y.')

    def test_variable_desconocida_se_deja_vacia_sin_reventar(self):
        resultado = _renderizar_plantilla('Hola {{ nombre }}{{ inexistente }}.', {'nombre': 'Ana'})
        self.assertEqual(resultado, 'Hola Ana.')

    def test_escapa_el_valor_insertado_pero_no_el_html_alrededor(self):
        resultado = _renderizar_plantilla('<p>{{ nombre }}</p>', {'nombre': '<script>alert(1)</script>'})
        self.assertEqual(resultado, '<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>')

    def test_sustituye_aunque_el_editor_haya_convertido_los_espacios_en_nbsp(self):
        # Quill (editor de texto enriquecido, `EmailTemplatesPage.jsx`) reescribe el HTML al
        # guardar y convierte espacios normales en `&nbsp;` — sobre todo justo alrededor de
        # `{{`/`}}`. Sin esto, cualquier plantilla editada desde el editor deja de sustituir.
        resultado = _renderizar_plantilla('<h1>{{&nbsp;site_name&nbsp;}}</h1>', {'site_name': 'ACME'})
        self.assertEqual(resultado, '<h1>ACME</h1>')

    def test_no_ejecuta_sintaxis_de_template_de_django_si_el_html_la_contiene(self):
        # Un HTML guardado por un admin con `{% ... %}` (sea a propósito o sin querer) se deja
        # literal — no es una etiqueta de Django real acá, es solo texto.
        resultado = _renderizar_plantilla('{% if True %}{{ nombre }}{% endif %}', {'nombre': 'Ana'})
        self.assertEqual(resultado, '{% if True %}Ana{% endif %}')


class EmailTemplateModelTests(TestCase):
    def test_get_or_seed_crea_la_fila_con_los_valores_por_defecto_si_no_existe(self):
        EmailTemplate.objects.all().delete()
        plantilla = EmailTemplate.get_or_seed(EmailTemplate.KEY_PASSWORD_RESET)
        self.assertIn('{{ site_name }}', plantilla.subject)
        self.assertIn('{{ enlace }}', plantilla.html_body)

    def test_get_or_seed_no_pisa_una_plantilla_ya_personalizada(self):
        EmailTemplate.objects.filter(key=EmailTemplate.KEY_PASSWORD_RESET).update(subject='Asunto personalizado')
        plantilla = EmailTemplate.get_or_seed(EmailTemplate.KEY_PASSWORD_RESET)
        self.assertEqual(plantilla.subject, 'Asunto personalizado')

    def test_restablecer_vuelve_a_los_valores_por_defecto(self):
        plantilla = EmailTemplate.get_or_seed(EmailTemplate.KEY_PASSWORD_RESET)
        plantilla.subject = 'Asunto personalizado'
        plantilla.html_body = '<p>a medida</p>'
        plantilla.save()
        plantilla.restablecer()
        plantilla.refresh_from_db()
        self.assertIn('{{ site_name }}', plantilla.subject)
        self.assertIn('{{ enlace }}', plantilla.html_body)


class EmailTemplateAdminViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')

    def _cliente_con_permiso(self, codename):
        from django.contrib.auth.models import Permission
        usuario = User.objects.create_user(
            username=f'user_{User.objects.count()}', email=f'user{User.objects.count()}@example.com',
            password='Clave-Segura-123',
        )
        usuario.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label='permissions'))
        cliente = APIClient()
        cliente.force_authenticate(user=usuario)
        return cliente

    def test_get_requiere_configuracion_ver(self):
        usuario = User.objects.create_user(username='sin_permiso', email='sp@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        resp = self.client.get('/api/auth/admin/email-templates/password_reset')
        self.assertEqual(resp.status_code, 403)

    def test_get_con_configuracion_ver_devuelve_la_plantilla(self):
        cliente = self._cliente_con_permiso('configuracion.ver')
        resp = cliente.get('/api/auth/admin/email-templates/password_reset')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['key'], 'password_reset')
        self.assertIn('html_body', resp.json())
        self.assertTrue(len(resp.json()['variables']) > 0)

    def test_get_con_key_invalida_devuelve_404(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/auth/admin/email-templates/no-existe')
        self.assertEqual(resp.status_code, 404)

    def test_patch_requiere_configuracion_editar_no_alcanza_con_ver(self):
        cliente = self._cliente_con_permiso('configuracion.ver')
        resp = cliente.patch('/api/auth/admin/email-templates/password_reset', {'subject': 'Nuevo asunto'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_patch_con_configuracion_editar_actualiza_y_audita(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch('/api/auth/admin/email-templates/password_reset', {
            'subject': 'Asunto nuevo', 'html_body': '<p>Hola {{ nombre_usuario }}</p>',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['subject'], 'Asunto nuevo')

        plantilla = EmailTemplate.objects.get(key='password_reset')
        self.assertEqual(plantilla.html_body, '<p>Hola {{ nombre_usuario }}</p>')
        self.assertEqual(plantilla.updated_by, self.admin)
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.SYSTEM_CONFIGURATION, action='EMAIL_TEMPLATE_UPDATED', actor=self.admin,
        ).exists())

    def test_reset_requiere_configuracion_editar(self):
        cliente = self._cliente_con_permiso('configuracion.ver')
        resp = cliente.post('/api/auth/admin/email-templates/password_reset/reset')
        self.assertEqual(resp.status_code, 403)

    def test_reset_vuelve_al_html_por_defecto(self):
        self.client.force_authenticate(user=self.admin)
        self.client.patch('/api/auth/admin/email-templates/password_reset', {'subject': 'A medida'}, format='json')

        resp = self.client.post('/api/auth/admin/email-templates/password_reset/reset')

        self.assertEqual(resp.status_code, 200)
        self.assertIn('{{ site_name }}', resp.json()['subject'])

    def test_el_correo_de_recuperacion_usa_la_plantilla_personalizada(self):
        self.client.force_authenticate(user=self.admin)
        self.client.patch('/api/auth/admin/email-templates/password_reset', {
            'subject': 'Un asunto bien distinto',
            'html_body': '<p>Hola {{ nombre_usuario }}, entrá acá: {{ enlace }}</p>',
        }, format='json')
        usuario = User.objects.create_user(username='fer', email='fer@example.com', password='Clave-Segura-123')

        PasswordResetService.solicitar(email='fer@example.com')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Un asunto bien distinto')
        self.assertIn('Hola fer,', mail.outbox[0].body)


class FortalezaDeContrasenaTests(TestCase):
    """SEC-04: `AUTH_PASSWORD_VALIDATORS` estaba configurado y nunca se invocaba.

    Lo único que se aplicaba era un `min_length=8` a mano, así que `12345678` (solo numérica),
    `password` (lista de contraseñas comunes) y el propio nombre de usuario se aceptaban.
    """

    def setUp(self):
        self.client = APIClient()
        self.usuario = User.objects.create_user(
            username='ana.perez', email='ana@example.com', password='Clave-Segura-123',
        )
        self.client.force_authenticate(user=self.usuario)

    def _cambiar(self, nueva):
        return self.client.post(
            '/api/auth/password/change',
            {'old_password': 'Clave-Segura-123', 'new_password': nueva}, format='json',
        )

    def test_rechaza_contrasena_solo_numerica(self):
        self.assertEqual(self._cambiar('12345678').status_code, 400)

    def test_rechaza_contrasena_comun(self):
        self.assertEqual(self._cambiar('password').status_code, 400)

    def test_rechaza_contrasena_parecida_al_nombre_de_usuario(self):
        self.assertEqual(self._cambiar('ana.perez').status_code, 400)

    def test_rechaza_contrasena_demasiado_corta(self):
        self.assertEqual(self._cambiar('Ab3d').status_code, 400)

    def test_acepta_una_contrasena_fuerte(self):
        self.assertEqual(self._cambiar('Trueno-Violeta-88').status_code, 204)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('Trueno-Violeta-88'))


class CambioDeContrasenaPropiaRevocaSesionesTests(TestCase):
    """SEC-07: era la única de las tres rutas que cambian contraseña que no revocaba sesiones.

    Es la más importante para el caso de uso: quien cambia su clave porque sospecha que le robaron
    el acceso esperaba invalidar la sesión del atacante.
    """

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')

    def _login(self):
        return self.client.post(
            '/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json',
        ).json()

    def test_revoca_las_otras_sesiones_y_conserva_la_actual(self):
        sesion_atacante = self._login()
        sesion_propia = self._login()

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {sesion_propia["access"]}')
        resp = self.client.post(
            '/api/auth/password/change',
            {'old_password': 'Clave-Segura-123', 'new_password': 'Trueno-Violeta-88'}, format='json',
        )
        self.assertEqual(resp.status_code, 204)

        # La sesión con la que se hizo el cambio sigue sirviendo...
        self.assertEqual(self.client.get('/api/auth/me').status_code, 200)

        # ...y la otra dejó de servir.
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {sesion_atacante["access"]}')
        self.assertEqual(self.client.get('/api/auth/me').status_code, 401)


class RotacionDeRefreshTokenTests(TestCase):
    """SEC-11: sin rotación, el `jti` nunca cambiaba y la detección de reutilización de
    `refresh_tokens` era una rama inalcanzable."""

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        self.tokens = self.client.post(
            '/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json',
        ).json()

    def test_el_refresco_devuelve_un_refresh_nuevo(self):
        resp = self.client.post('/api/auth/token/refresh', {'refresh': self.tokens['refresh']}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('refresh', resp.json())
        self.assertNotEqual(resp.json()['refresh'], self.tokens['refresh'])

    def test_reutilizar_un_refresh_viejo_revoca_la_sesion_completa(self):
        nuevo = self.client.post(
            '/api/auth/token/refresh', {'refresh': self.tokens['refresh']}, format='json',
        ).json()['refresh']

        # El viejo ya no es el vigente: se interpreta como token robado y cae la sesión entera.
        resp = self.client.post('/api/auth/token/refresh', {'refresh': self.tokens['refresh']}, format='json')
        self.assertEqual(resp.json()['error'], 'REFRESH_TOKEN_REUTILIZADO')

        # Incluso el refresh legítimo emitido antes del incidente deja de servir.
        resp = self.client.post('/api/auth/token/refresh', {'refresh': nuevo}, format='json')
        self.assertEqual(resp.json()['error'], 'SESION_INACTIVA')


class LoginThrottleTests(TestCase):
    """SEC-06: el login no tenía ningún límite de tasa.

    Los throttles quedan desactivados durante `manage.py test` (ver el comentario en
    `config/settings.py`: su contador vive en la caché, que no se reinicia entre tests, así que
    con los límites activos el test número N falla por el consumo de los N-1 anteriores). Esta
    clase los reactiva a un límite bajo para verificar que efectivamente aplican.

    Se parchea `SimpleRateThrottle.THROTTLE_RATES` y no los settings porque DRF lee las tasas en
    un atributo de clase que se fija al importar el módulo: `override_settings` no lo alcanza.
    """

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='ana', email='ana@example.com', password='Clave-Segura-123')
        parche = mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'login': '3/min'})
        parche.start()
        self.addCleanup(parche.stop)
        # El contador es por IP y vive en la caché del proceso: hay que partir de cero.
        cache.clear()
        self.addCleanup(cache.clear)

    def test_supera_el_limite_de_tasa_y_responde_429(self):
        for _ in range(3):
            self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'incorrecta'}, format='json')

        resp = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.status_code, 429)

    def test_por_debajo_del_limite_el_login_funciona_normalmente(self):
        resp = self.client.post('/api/auth/login', {'identifier': 'ana', 'password': 'Clave-Segura-123'}, format='json')
        self.assertEqual(resp.status_code, 200)
