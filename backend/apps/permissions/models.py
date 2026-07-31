from django.db import models

from .catalog import as_django_permission_tuples


class ModulePermission(models.Model):
    """Modelo ancla (sin tabla propia) que cuelga el catálogo cerrado de permisos como
    `auth.Permission` reales, para poder asignarlos a `Group`/`user.user_permissions` con la
    infraestructura nativa de Django."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = as_django_permission_tuples()
