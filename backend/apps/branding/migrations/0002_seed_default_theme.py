"""Crea la única fila de `SiteTheme` (si no existe) sembrada con la paleta actual de
`dashboard.css`, para que activar branding no cambie la identidad visual el día 1."""

from django.db import migrations

from apps.branding.catalog import DEFAULT_THEME


def sembrar_tema_por_defecto(apps, schema_editor):
    """`DEFAULT_THEME` se importa en vivo desde `catalog.py` (no está congelado en esta
    migración) — si una migración posterior le agrega campos al modelo (p. ej. 0003, colores de
    Bootstrap), esta migración histórica solo conoce los campos que existían en 0001. Se filtra
    a los campos reales del modelo congelado para que una instalación nueva (que aplica todas las
    migraciones en orden) no falle por un argumento desconocido."""
    SiteTheme = apps.get_model('branding', 'SiteTheme')
    if not SiteTheme.objects.filter(pk=1).exists():
        campos_conocidos = {campo.name for campo in SiteTheme._meta.get_fields()}
        valores = {clave: valor for clave, valor in DEFAULT_THEME.items() if clave in campos_conocidos}
        SiteTheme.objects.create(pk=1, **valores)


def no_revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('branding', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(sembrar_tema_por_defecto, no_revertir),
    ]
