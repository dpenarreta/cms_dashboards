import hashlib
import logging
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from cartera.exceptions import CarteraError

from .models import LoginAttempt, PasswordResetToken, Session
from .tokens import issue_token_pair

User = get_user_model()
logger = logging.getLogger(__name__)

# Nunca revela si el correo existe (sección 7.2 del prompt: mensaje siempre genérico).
MENSAJE_GENERICO_RECUPERACION = 'Si el correo está registrado, recibirás un enlace para restablecer tu contraseña.'

# Hash señuelo: comparar contra esto cuando el identificador no resuelve a ningún usuario, para
# que el tiempo de respuesta no delate si el usuario existe o no.
_DUMMY_PASSWORD_HASH = 'argon2$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$ZmFrZWhhc2h2YWx1ZQ'


class BruteForceProtectionService:
    @staticmethod
    def esta_bloqueado(identifier):
        limite = getattr(settings, 'LOGIN_MAX_FAILED_ATTEMPTS', 5)
        minutos = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)
        desde = timezone.now() - timezone.timedelta(minutes=minutos)
        fallidos = LoginAttempt.objects.filter(identifier=identifier, successful=False, created_at__gte=desde).count()
        exitosos_recientes = LoginAttempt.objects.filter(
            identifier=identifier, successful=True, created_at__gte=desde,
        ).exists()
        return fallidos >= limite and not exitosos_recientes

    @staticmethod
    def registrar_intento(*, identifier, ip_address, user=None, successful):
        LoginAttempt.objects.create(identifier=identifier, ip_address=ip_address, user=user, successful=successful)


class SessionService:
    @staticmethod
    def crear(*, user, refresh_token_jti, device='', user_agent='', ip_address=None):
        expira = timezone.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
        return Session.objects.create(
            user=user, refresh_token_jti=refresh_token_jti, device=device,
            user_agent=user_agent, ip_address=ip_address, expires_at=expira,
        )

    @staticmethod
    def revocar_todas(user):
        Session.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())


class AuthenticationService:
    @staticmethod
    def login(*, identifier, password, ip_address=None, user_agent=''):
        if BruteForceProtectionService.esta_bloqueado(identifier):
            raise CarteraError(
                'Demasiados intentos fallidos. Intenta de nuevo más tarde.', codigo='CUENTA_BLOQUEADA_TEMPORALMENTE',
            )

        usuario = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()

        if usuario is None:
            check_password('cualquier-cosa', _DUMMY_PASSWORD_HASH)
            BruteForceProtectionService.registrar_intento(identifier=identifier, ip_address=ip_address, successful=False)
            raise CarteraError('Usuario o contraseña incorrectos.', codigo='CREDENCIALES_INVALIDAS')

        credenciales_validas = usuario.check_password(password)
        if not credenciales_validas or not usuario.is_active:
            BruteForceProtectionService.registrar_intento(identifier=identifier, ip_address=ip_address, user=usuario, successful=False)
            log_event(
                domain=AuditEvent.Domain.AUTHENTICATION, action='LOGIN_FAILED', result=AuditEvent.Result.FAILED,
                actor=usuario, entity_type='user', entity_id=usuario.id, ip_address=ip_address, user_agent=user_agent,
            )
            raise CarteraError('Usuario o contraseña incorrectos.', codigo='CREDENCIALES_INVALIDAS')

        BruteForceProtectionService.registrar_intento(identifier=identifier, ip_address=ip_address, user=usuario, successful=True)

        refresh = RefreshToken.for_user(usuario)
        sesion = SessionService.crear(user=usuario, refresh_token_jti=str(refresh['jti']), user_agent=user_agent, ip_address=ip_address)
        refresh['sid'] = str(sesion.id)
        access = refresh.access_token
        access['sid'] = str(sesion.id)

        log_event(
            domain=AuditEvent.Domain.AUTHENTICATION, action='LOGIN_SUCCESS', actor=usuario,
            entity_type='user', entity_id=usuario.id, ip_address=ip_address, user_agent=user_agent,
        )
        return {'access': str(access), 'refresh': str(refresh)}, usuario

    @staticmethod
    def refresh_tokens(*, refresh_token_str):
        try:
            token = RefreshToken(refresh_token_str)
        except TokenError:
            raise CarteraError('El token de actualización no es válido o expiró.', codigo='REFRESH_TOKEN_INVALIDO')

        sid = token.get('sid')
        try:
            sesion = Session.objects.get(id=sid)
        except (Session.DoesNotExist, ValueError, TypeError):
            raise CarteraError('La sesión ya no existe.', codigo='SESION_INEXISTENTE')

        if str(token['jti']) != sesion.refresh_token_jti:
            # El refresh presentado no es el vigente para esta sesión: posible reutilización de
            # un token robado/rotado. Se revoca la sesión completa por precaución.
            sesion.revoke()
            raise CarteraError('El token de actualización ya no es válido.', codigo='REFRESH_TOKEN_REUTILIZADO')

        if not sesion.is_active:
            raise CarteraError('La sesión expiró o fue revocada.', codigo='SESION_INACTIVA')

        access = token.access_token
        access['sid'] = str(sesion.id)
        sesion.save(update_fields=['last_used_at'])
        return {'access': str(access)}

    @staticmethod
    def logout(*, refresh_token_str):
        try:
            token = RefreshToken(refresh_token_str)
        except TokenError:
            return
        sid = token.get('sid')
        Session.objects.filter(id=sid, revoked_at__isnull=True).update(revoked_at=timezone.now())

    @staticmethod
    def logout_all(*, user):
        SessionService.revocar_todas(user)


def _hash_token(raw_token):
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def _enviar_correo_recuperacion(*, usuario, raw_token):
    from apps.branding.models import SiteTheme

    tema = SiteTheme.get_solo()
    minutos = int(getattr(settings, 'PASSWORD_RESET_TOKEN_LIFETIME_MINUTES', 30))
    enlace = f'{settings.FRONTEND_URL.rstrip("/")}/reset-password?token={raw_token}'
    contexto = {
        'nombre_usuario': usuario.first_name or usuario.username,
        'enlace': enlace,
        'minutos_expiracion': minutos,
        'site_name': tema.site_name,
        'color_primary': tema.color_primary,
    }
    html = render_to_string('authentication/password_reset_email.html', contexto)
    texto = render_to_string('authentication/password_reset_email.txt', contexto)

    correo = EmailMultiAlternatives(
        subject='Recuperación de contraseña | CMS Dashboards',
        body=strip_tags(texto),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario.email],
    )
    correo.attach_alternative(html, 'text/html')
    correo.send(fail_silently=False)


class PasswordResetService:
    """Recuperación de contraseña por correo (Módulo D). El mensaje de respuesta a
    `solicitar(...)` es siempre el mismo genérico, exista o no el correo — nunca revela si un
    usuario existe (sección 7.2/9.1 del prompt)."""

    @staticmethod
    def solicitar(*, email, request=None, ip_address=None, user_agent=''):
        usuario = User.objects.filter(email__iexact=email.strip()).first()

        log_event(
            domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_REQUESTED',
            actor=usuario, entity_type='user', entity_id=usuario.id if usuario else '',
            metadata={'email_domain': email.split('@')[-1] if '@' in email else ''},
            ip_address=ip_address, user_agent=user_agent, request=request,
        )

        if usuario is None or not usuario.is_active:
            return MENSAJE_GENERICO_RECUPERACION

        # Invalida cualquier token anterior sin usar antes de emitir uno nuevo.
        PasswordResetToken.objects.filter(user=usuario, used_at__isnull=True).update(used_at=timezone.now())

        raw_token = secrets.token_urlsafe(32)
        minutos = int(getattr(settings, 'PASSWORD_RESET_TOKEN_LIFETIME_MINUTES', 30))
        token = PasswordResetToken.objects.create(
            user=usuario, token_hash=_hash_token(raw_token),
            expires_at=timezone.now() + timezone.timedelta(minutes=minutos),
        )

        try:
            _enviar_correo_recuperacion(usuario=usuario, raw_token=raw_token)
        except Exception:
            logger.exception('No se pudo enviar el correo de recuperación de contraseña (user_id=%s)', usuario.id)
            log_event(
                domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_EMAIL_FAILED',
                result=AuditEvent.Result.FAILED, actor=usuario, entity_type='user', entity_id=usuario.id,
                metadata={'token_id': str(token.id)}, ip_address=ip_address, user_agent=user_agent, request=request,
            )
            return MENSAJE_GENERICO_RECUPERACION

        log_event(
            domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_EMAIL_SENT',
            actor=usuario, entity_type='user', entity_id=usuario.id,
            metadata={'token_id': str(token.id)}, ip_address=ip_address, user_agent=user_agent, request=request,
        )
        return MENSAJE_GENERICO_RECUPERACION

    @staticmethod
    def validar(*, raw_token, request=None, ip_address=None, user_agent=''):
        token = PasswordResetToken.objects.select_related('user').filter(token_hash=_hash_token(raw_token)).first()

        if token is None:
            log_event(
                domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_TOKEN_INVALID',
                result=AuditEvent.Result.FAILED, ip_address=ip_address, user_agent=user_agent, request=request,
            )
            raise CarteraError('El enlace de recuperación no es válido.', codigo='TOKEN_INVALIDO')

        if token.used_at is not None:
            log_event(
                domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_TOKEN_INVALID',
                result=AuditEvent.Result.FAILED, actor=token.user, entity_type='user', entity_id=token.user_id,
                ip_address=ip_address, user_agent=user_agent, request=request,
            )
            raise CarteraError('El enlace de recuperación no es válido.', codigo='TOKEN_INVALIDO')

        if token.expires_at <= timezone.now():
            log_event(
                domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_TOKEN_EXPIRED',
                result=AuditEvent.Result.FAILED, actor=token.user, entity_type='user', entity_id=token.user_id,
                ip_address=ip_address, user_agent=user_agent, request=request,
            )
            raise CarteraError('El enlace de recuperación expiró. Solicita uno nuevo.', codigo='TOKEN_EXPIRADO')

        return token

    @staticmethod
    def confirmar(*, raw_token, new_password, request=None, ip_address=None, user_agent=''):
        token = PasswordResetService.validar(raw_token=raw_token, request=request, ip_address=ip_address, user_agent=user_agent)
        usuario = token.user

        if not usuario.is_active:
            raise CarteraError('El enlace de recuperación no es válido.', codigo='TOKEN_INVALIDO')

        usuario.set_password(new_password)
        usuario.must_change_password = False
        usuario.save(update_fields=['password', 'must_change_password'])
        token.marcar_usado()
        SessionService.revocar_todas(usuario)

        log_event(
            domain=AuditEvent.Domain.AUTHENTICATION, action='PASSWORD_RESET_COMPLETED',
            actor=usuario, entity_type='user', entity_id=usuario.id,
            ip_address=ip_address, user_agent=user_agent, request=request,
        )
        return usuario
