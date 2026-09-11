from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Fuente única de auditoría (Módulo A, trabajo futuro post-integración). Unifica lo que
    antes eran dos tablas separadas (`apps.core.AuditLog` para seguridad/administración y
    `cartera.DashboardAuditLog` para cambios de layout), conservando el contexto de cada dominio
    en vez de aplanarlo en un esquema genérico sin clasificación."""

    class Domain(models.TextChoices):
        SECURITY = 'SECURITY', 'Seguridad'
        AUTHENTICATION = 'AUTHENTICATION', 'Autenticación'
        USER_MANAGEMENT = 'USER_MANAGEMENT', 'Gestión de usuarios'
        ROLE_MANAGEMENT = 'ROLE_MANAGEMENT', 'Gestión de roles'
        PERMISSION_MANAGEMENT = 'PERMISSION_MANAGEMENT', 'Gestión de permisos'
        DASHBOARD_ACCESS = 'DASHBOARD_ACCESS', 'Acceso a dashboard'
        DASHBOARD_LAYOUT = 'DASHBOARD_LAYOUT', 'Diseño de dashboard'
        DASHBOARD_CONFIGURATION = 'DASHBOARD_CONFIGURATION', 'Configuración de dashboard'
        DATA_SOURCE = 'DATA_SOURCE', 'Fuente de datos'
        EXPORT = 'EXPORT', 'Exportación'
        FILE_UPLOAD = 'FILE_UPLOAD', 'Carga de archivo'
        SYSTEM_CONFIGURATION = 'SYSTEM_CONFIGURATION', 'Configuración del sistema'

    class Result(models.TextChoices):
        SUCCESS = 'SUCCESS', 'Éxito'
        FAILED = 'FAILED', 'Fallido'
        DENIED = 'DENIED', 'Denegado'
        WARNING = 'WARNING', 'Advertencia'

    class Severity(models.TextChoices):
        INFO = 'INFO', 'Info'
        LOW = 'LOW', 'Baja'
        MEDIUM = 'MEDIUM', 'Media'
        HIGH = 'HIGH', 'Alta'
        CRITICAL = 'CRITICAL', 'Crítica'

    domain = models.CharField(max_length=30, choices=Domain.choices, db_index=True)
    action = models.CharField(max_length=100, db_index=True)
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.SUCCESS, db_index=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO, db_index=True)

    # `actor` puede volverse NULL si el usuario se elimina más adelante; `actor_username` es una
    # foto del nombre en el momento del evento, para que el historial siga siendo legible.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events',
    )
    actor_username = models.CharField(max_length=150, blank=True, default='')

    entity_type = models.CharField(max_length=100, blank=True, default='')
    entity_id = models.CharField(max_length=64, blank=True, default='')
    entity_name = models.CharField(max_length=255, blank=True, default='')

    dashboard_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    component_id = models.CharField(max_length=100, blank=True, default='')

    request_id = models.CharField(max_length=64, blank=True, default='')
    session_id = models.CharField(max_length=64, blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default='')

    previous_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    message = models.CharField(max_length=500, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.domain}] {self.action} ({self.result})'

    @property
    def actor_username_actual(self):
        """Nombre del actor resuelto por la clave foránea cuando la cuenta todavía existe, y solo
        entonces cae a la foto guardada en `actor_username`.

        Un usuario puede cambiar su propio `username` (`UpdateMyProfileSerializer`), así que la
        foto se vuelve engañosa: los eventos viejos siguen mostrando el nombre anterior y —peor—
        alguien puede adoptar un nombre que otra persona dejó libre y aparecer con él en el
        historial ajeno. La clave foránea es la identidad real; `actor_username` queda como
        respaldo para cuentas ya eliminadas (`on_delete=SET_NULL`), que es el caso para el que se
        agregó.

        Requiere `select_related('actor')` en el queryset para no hacer una consulta por fila.
        """
        if self.actor_id and self.actor is not None:
            return self.actor.username
        return self.actor_username or ''
