"""Otorga los permisos nuevos `dashboard.fuente_bd.configurar`/`dashboard.fuente_bd.actualizar`
(agregados al catálogo para separar quién puede apuntar un dashboard a una vista/procedimiento de
la base de datos productiva y quién puede forzar una recarga de datos, de los permisos genéricos
`dashboard.editar`/`dashboard.view` que se usaban antes) al rol ADMINISTRADOR_GENERAL — igual que
en las migraciones 0002/0003/0004, un permiso nuevo en el catálogo no se asigna automáticamente a
un grupo ya creado.

Reutiliza la misma lógica idempotente (importa `PERMISSION_CATALOG` en vivo, no congelado, y usa
`.set(...)` con el catálogo COMPLETO actual)."""

from django.db import migrations

NOMBRE_ROL_ADMINISTRADOR_GENERAL = 'ADMINISTRADOR_GENERAL'


def resembrar_administrador_general(apps, schema_editor):
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
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('roles', '0004_agregar_permisos_ia_a_administrador_general'),
        ('permissions', '0004_alter_modulepermission_options'),
    ]

    operations = [
        migrations.RunPython(resembrar_administrador_general, no_revertir),
    ]
