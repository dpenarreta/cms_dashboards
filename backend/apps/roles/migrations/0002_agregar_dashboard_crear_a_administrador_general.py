"""Otorga el permiso nuevo `dashboard.crear` (agregado al catálogo para el Módulo de creación de
dashboards por área) al rol ADMINISTRADOR_GENERAL — la migración `0001_initial` solo sembró el
catálogo vigente en ese momento; agregar un permiso nuevo al catálogo después no lo asigna
automáticamente a un grupo ya creado.

Reutiliza la misma lógica idempotente de `0001_initial` (importa `PERMISSION_CATALOG` en vivo, no
congelado, y usa `.set(...)` con el catálogo COMPLETO actual) — sincroniza el grupo con el
catálogo vigente sin quitarle ningún permiso que ya tuviera, y sin duplicar filas si se vuelve a
ejecutar."""

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
        ('roles', '0001_initial'),
        ('permissions', '0002_alter_modulepermission_options'),
    ]

    operations = [
        migrations.RunPython(resembrar_administrador_general, no_revertir),
    ]
