import hashlib
import logging
import re
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.utils import timezone
from django.utils.html import escape, strip_tags
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.password import validar_fortaleza
from cartera.exceptions import CarteraError

from .models import EmailTemplate, LoginAttempt, PasswordResetToken, Session
from .tokens import issue_token_pair

User = get_user_model()
logger = logging.getLogger(__name__)

# Nunca revela si el correo existe (sección 7.2 del prompt: mensaje siempre genérico).
MENSAJE_GENERICO_RECUPERACION = 'Si el correo está registrado, recibirás un enlace para restablecer tu contraseña.'

# Hash señuelo: comparar contra esto cuando el identificador no resuelve a ningún usuario, para
# que el tiempo de respuesta no delate si el usuario existe o no.
_DUMMY_PASSWORD_HASH = 'argon2$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$ZmFrZWhhc2h2YWx1ZQ'


class BruteForceProtectionService:
    """Bloqueo temporal de intentos de login, en dos ejes independientes.

    **Por cuenta**, contra un identificador CANÓNICO (`identificador_canonico`), no contra el
    texto que se escribió. Antes se contaba el valor crudo, y como el login acepta indistintamente
    el username o el email, `admin` y `admin@empresa.com` llevaban contadores separados: 5
    intentos con uno y 5 más con el otro, sobre la misma cuenta, sin bloqueo — y cada alias de
    correo sumaba otros 5. La variación de mayúsculas era el mismo agujero, tapado solo por la
    colación case-insensitive de SQL Server, así que reaparecía con `DB_ENGINE=sqlite`.

    **Por IP**, con un umbral propio más alto. El eje por cuenta no ve el patrón de probar una
    contraseña habitual contra cientos de cuentas distintas desde la misma máquina, porque cada
    cuenta recibe un único intento fallido. Complementa (no reemplaza) el `ScopedRateThrottle` de
    `LoginView`, que limita la tasa; esto limita el total acumulado en la ventana.
    """

    @staticmethod
    def identificador_canonico(identifier, usuario=None):
        """Un único valor por cuenta, sea cual sea el campo por el que se intente entrar.

        Cuando el identificador resuelve a un usuario se usa su clave primaria; cuando no resuelve
        (cuenta inexistente) se cae al texto normalizado en minúsculas, que además evita depender
        de cómo compare cadenas el motor de base de datos. Se sigue contando por identificador y
        nunca por usuario "ya resuelto y existente", así que enumerar cuentas no se vuelve gratis:
        un identificador inexistente también acumula y también bloquea.
        """
        if usuario is not None:
            return f'user:{usuario.pk}'
        return (identifier or '').strip().lower()[:255]

    @staticmethod
    def esta_bloqueado(identificador_canonico, ip_address=None):
        limite = getattr(settings, 'LOGIN_MAX_FAILED_ATTEMPTS', 5)
        limite_ip = getattr(settings, 'LOGIN_MAX_FAILED_ATTEMPTS_PER_IP', 30)
        minutos = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)
        desde = timezone.now() - timezone.timedelta(minutes=minutos)

        fallidos = LoginAttempt.objects.filter(
            identifier=identificador_canonico, successful=False, created_at__gte=desde,
        ).count()
        exitosos_recientes = LoginAttempt.objects.filter(
            identifier=identificador_canonico, successful=True, created_at__gte=desde,
        ).exists()
        if fallidos >= limite and not exitosos_recientes:
            return True

        # El eje por IP no tiene la salida de "hubo un éxito reciente": un atacante que acierta
        # una cuenta entre cientos no debería con eso habilitarse a seguir probando el resto.
        if ip_address and limite_ip:
            fallidos_ip = LoginAttempt.objects.filter(
                ip_address=ip_address, successful=False, created_at__gte=desde,
            ).count()
            if fallidos_ip >= limite_ip:
                return True

        return False

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

    @staticmethod
    def revocar_todas_menos(user, sesion_id):
        """Revoca todas las sesiones del usuario salvo una — la que está usando ahora mismo.

        Lo usa el cambio de contraseña propio: quien cambia su clave porque sospecha que le
        robaron el acceso espera que las demás sesiones caigan, pero no que lo expulse a él de la
        pantalla en la que está.
        """
        Session.objects.filter(user=user, revoked_at__isnull=True).exclude(id=sesion_id).update(
            revoked_at=timezone.now(),
        )


class AuthenticationService:
    @staticmethod
    def login(*, identifier, password, ip_address=None, user_agent=''):
        # El usuario se resuelve ANTES de consultar el bloqueo para poder canonicalizar el
        # identificador (ver `BruteForceProtectionService.identificador_canonico`): sin eso, el
        # contador dependía del texto exacto que se escribió y alternar username/email lo
        # duplicaba. Resolver primero no filtra información — la respuesta y el tiempo de
        # respuesta siguen siendo los mismos exista o no la cuenta.
        usuario = User.objects.filter(Q(username__iexact=identifier) | Q(email__iexact=identifier)).first()
        canonico = BruteForceProtectionService.identificador_canonico(identifier, usuario)

        if BruteForceProtectionService.esta_bloqueado(canonico, ip_address=ip_address):
            raise CarteraError(
                'Demasiados intentos fallidos. Intenta de nuevo más tarde.', codigo='CUENTA_BLOQUEADA_TEMPORALMENTE',
            )

        if usuario is None:
            check_password('cualquier-cosa', _DUMMY_PASSWORD_HASH)
            BruteForceProtectionService.registrar_intento(identifier=canonico, ip_address=ip_address, successful=False)
            raise CarteraError('Usuario o contraseña incorrectos.', codigo='CREDENCIALES_INVALIDAS')

        credenciales_validas = usuario.check_password(password)
        if not credenciales_validas or not usuario.is_active:
            BruteForceProtectionService.registrar_intento(identifier=canonico, ip_address=ip_address, user=usuario, successful=False)
            log_event(
                domain=AuditEvent.Domain.AUTHENTICATION, action='LOGIN_FAILED', result=AuditEvent.Result.FAILED,
                actor=usuario, entity_type='user', entity_id=usuario.id, ip_address=ip_address, user_agent=user_agent,
            )
            raise CarteraError('Usuario o contraseña incorrectos.', codigo='CREDENCIALES_INVALIDAS')

        BruteForceProtectionService.registrar_intento(identifier=canonico, ip_address=ip_address, user=usuario, successful=True)

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

        # Rotación: se emite un refresh nuevo y se guarda su `jti` como el único vigente de la
        # sesión. Es lo que vuelve efectiva la detección de reutilización de unas líneas más
        # arriba — sin rotar, el `jti` nunca cambiaba y esa rama era inalcanzable. A partir de
        # acá, presentar un refresh viejo (por ejemplo uno robado, después de que el usuario
        # legítimo refrescó) revoca la sesión completa en vez de pasar inadvertido.
        refresh_nuevo = RefreshToken.for_user(sesion.user)
        refresh_nuevo['sid'] = str(sesion.id)
        access_nuevo = refresh_nuevo.access_token
        access_nuevo['sid'] = str(sesion.id)
        sesion.refresh_token_jti = str(refresh_nuevo['jti'])
        sesion.save(update_fields=['refresh_token_jti', 'last_used_at'])

        return {'access': str(access_nuevo), 'refresh': str(refresh_nuevo)}

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


# `(?:\s|&nbsp;)*`, no solo `\s*`: el editor de texto enriquecido (Quill, `EmailTemplatesPage.jsx`)
# reescribe el HTML al guardar y convierte espacios normales en la entidad literal `&nbsp;`
# (6 caracteres de texto, no el carácter Unicode — comportamiento normal de un contenteditable
# para que el navegador no colapse esos espacios visualmente) — pasa sobre todo justo alrededor de
# `{{`/`}}`, que es exactamente donde este patrón necesita reconocer espacio. Sin este ajuste, un
# admin que edita la plantilla desde el editor rompe la sustitución de variables sin darse cuenta.
_MARCADOR_RE = re.compile(r'\{\{(?:\s|&nbsp;)*(\w+)(?:\s|&nbsp;)*\}\}')


def _renderizar_plantilla(texto, contexto):
    """Sustitución de `{{ variable }}` propia y deliberadamente simple — NO el motor de templates
    de Django (`Template(texto).render(...)`), que permitiría `{% %}` y ejecutar lógica arbitraria
    sobre HTML que guardó un admin desde el editor de texto enriquecido de `/admin/settings`. El
    HTML alrededor de cada marcador se deja tal cual (confiado, mismo nivel que ya tiene un admin
    para editar `SiteTheme`); el VALOR que se inserta si se escapa (`django.utils.html.escape`)
    para que un dato como `first_name`/`username` con caracteres especiales no rompa la
    estructura del HTML. Una clave sin valor en `contexto` se deja vacía, no revienta."""
    def _reemplazar(match):
        return escape(str(contexto.get(match.group(1), '')))
    return _MARCADOR_RE.sub(_reemplazar, texto)


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
    plantilla = EmailTemplate.get_or_seed(EmailTemplate.KEY_PASSWORD_RESET)
    asunto = _renderizar_plantilla(plantilla.subject, contexto)
    html = _renderizar_plantilla(plantilla.html_body, contexto)

    correo = EmailMultiAlternatives(
        subject=asunto,
        body=strip_tags(html),
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

        # Recién acá se conoce a quién pertenece el token, así que este es el único punto donde
        # `UserAttributeSimilarityValidator` puede comparar la contraseña nueva contra los datos
        # del usuario. Los demás validadores ya corrieron en el serializer.
        validar_fortaleza(new_password, usuario)

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
