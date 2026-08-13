import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Session(BaseModel):
    """Una sesión = un par de tokens JWT emitido. Permite revocar/expirar sin depender de la
    blacklist genérica de simplejwt (ver docs/integracion/decisions.md #8)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
    refresh_token_jti = models.CharField(max_length=64, unique=True)
    device = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self):
        return self.revoked_at is None and self.expires_at > timezone.now()

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=['revoked_at'])


class LoginAttempt(BaseModel):
    """Registro de intentos de login (éxito/fracaso) por identificador, para la protección de
    fuerza bruta — indexado por `identifier`, no por usuario resuelto (evita enumeración)."""

    identifier = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    successful = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']


class PasswordResetToken(BaseModel):
    """Token de recuperación de contraseña de un solo uso (Módulo D, trabajo futuro
    post-integración). Solo se persiste el hash SHA-256 del token — el valor crudo únicamente
    existe en memoria mientras se genera el enlace del correo, nunca se guarda en texto plano."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()

    def marcar_usado(self):
        self.used_at = timezone.now()
        self.save(update_fields=['used_at'])


class EmailTemplate(BaseModel):
    """Plantilla de correo transaccional personalizable (asunto + HTML propio, editado desde un
    editor de texto enriquecido en `/admin/settings`) — un único `html_body` por plantilla, no un
    `.html`/`.txt` por separado: el cuerpo en texto plano del correo se deriva automáticamente
    quitándole las etiquetas (`strip_tags`, ver `services.py::_enviar_correo_recuperacion`), igual
    que ya hacían a mano los templates que reemplaza. `key` (no un singleton `pk=1` como
    `apps.branding.SiteTheme`) porque puede haber más de una plantilla — hoy solo
    `password_reset`, pensado para más tipos de correo a futuro sin agregar un modelo nuevo por
    cada uno.

    El HTML se guarda tal cual lo entrega el editor (confiado — solo un usuario con
    `configuracion.editar` puede escribirlo, mismo nivel de confianza que ya tiene para editar
    `SiteTheme`) y se le insertan valores dinámicos (`{{ nombre_usuario }}`, `{{ enlace }}`, etc.)
    con un reemplazo de texto simple y propio (`services.py::_renderizar_plantilla`) — NO el motor
    de templates de Django (`Template(...).render(...)`), que permitiría `{% %}` y ejecutar lógica
    arbitraria sobre el HTML guardado por un admin; los valores insertados sí se escapan
    (`django.utils.html.escape`) para que un `first_name`/`username` con caracteres especiales no
    rompa la estructura del HTML."""

    KEY_PASSWORD_RESET = 'password_reset'
    KEY_CHOICES = [
        (KEY_PASSWORD_RESET, 'Recuperación de contraseña'),
    ]

    key = models.CharField(max_length=50, unique=True, choices=KEY_CHOICES)
    subject = models.CharField(max_length=200)
    html_body = models.TextField()
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.key

    @classmethod
    def get_or_seed(cls, key):
        from .email_template_defaults import DEFAULT_EMAIL_TEMPLATES

        defecto = DEFAULT_EMAIL_TEMPLATES[key]
        instancia, _creada = cls.objects.get_or_create(
            key=key, defaults={'subject': defecto['subject'], 'html_body': defecto['html_body']},
        )
        return instancia

    def restablecer(self):
        from .email_template_defaults import DEFAULT_EMAIL_TEMPLATES

        defecto = DEFAULT_EMAIL_TEMPLATES[self.key]
        self.subject = defecto['subject']
        self.html_body = defecto['html_body']
        self.save(update_fields=['subject', 'html_body', 'updated_at'])
