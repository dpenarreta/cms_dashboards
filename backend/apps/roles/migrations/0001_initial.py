"""Siembra el rol ADMINISTRADOR_GENERAL con el catálogo completo de permisos.

`apps.roles` no tiene modelos propios (los "roles" son `django.contrib.auth.models.Group`), así
que esta es una migración puramente de datos. El nombre del rol es una decisión explícita del
usuario (docs/integracion/decisions.md #5) — no "Superusuario" como en el proyecto de origen.

Nota técnica: no se puede depender de que `ContentType`/`Permission` para `ModulePermission` ya
existan en este punto (esas filas normalmente las crea Django vía la señal `post_migrate`, que se
dispara DESPUÉS de que terminan de aplicarse TODAS las migraciones de una misma corrida de
`migrate` — y en una instalación nueva, `roles.0001_initial` corre en la MISMA corrida que
`permissions.0001_initial`). Por eso esta migración crea el `ContentType` y los `Permission` del
catálogo ella misma con `get_or_create` (idempotente: si `post_migrate` los crea después, no
duplica nada), en vez de asumir que ya existen.

El acceso "ve todo" de un administrador general no depende de pertenecer a este grupo: se
resuelve siempre por los permisos efectivamente asignados (ver `apps.permissions.authorization`).
Este grupo es solo un atajo para asignar el catálogo completo a cualquier cuenta.
"""

from django.db import migrations

NOMBRE_ROL_ADMINISTRADOR_GENERAL = 'ADMINISTRADOR_GENERAL'


def sembrar_rol_administrador_general(apps, schema_editor):
    from apps.permissions.catalog import PERMISSION_CATALOG

    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    Group = apps.get_model('auth', 'Group')

    content_type, _ = ContentType.objects.get_or_create(app_label='permissions', model='modulepermission')

    permisos = []
    for permiso in PERMISSION_CATALOG:
        objeto, _ = Permission.objects.get_or_create(
            content_type=content_type, codename=permiso['codename'],
            defaults={'name': permiso['name'][:255]},
        )
        permisos.append(objeto)

    grupo, _ = Group.objects.get_or_create(name=NOMBRE_ROL_ADMINISTRADOR_GENERAL)
    grupo.permissions.set(permisos)


def no_revertir(apps, schema_editor):
    """No se elimina el rol al revertir: podría estar asignado a usuarios reales."""
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('permissions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(sembrar_rol_administrador_general, no_revertir),
    ]
