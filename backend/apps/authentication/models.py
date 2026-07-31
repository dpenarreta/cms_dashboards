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
