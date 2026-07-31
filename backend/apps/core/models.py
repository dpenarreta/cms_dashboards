from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    """Timestamps compartidos por los modelos de las apps transversales (auth/usuarios/roles)."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(BaseModel):
    """Auditoría de seguridad (login, cambios de usuario/rol/permiso, accesos denegados).

    Dominio distinto de `cartera.DashboardAuditLog` (que audita cambios de layout del editor
    visual) — no se unifican en esta fase, ver docs/integracion/decisions.md #9.
    """

    class Result(models.TextChoices):
        SUCCESS = 'success', 'Éxito'
        FAILURE = 'failure', 'Fallido'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_actions',
    )
    action = models.CharField(max_length=100, db_index=True)
    module = models.CharField(max_length=50, blank=True, db_index=True)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    previous_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.SUCCESS)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.actor_id}: {self.action}'
