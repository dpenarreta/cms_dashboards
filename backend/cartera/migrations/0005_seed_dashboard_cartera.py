"""Siembra la fila 'cartera' en el nuevo modelo `Dashboard` (antes vivía solo como una entrada
estática en `dashboard_registry.DASHBOARD_REGISTRY`, ver decisión en
docs/integracion/decisions.md-style: `dashboards_autorizados` pasa a leer de esta tabla). No
destructiva: no borra ni modifica nada existente, solo crea la fila si no existe."""

from django.db import migrations


def sembrar_dashboard_cartera(apps, schema_editor):
    Dashboard = apps.get_model('cartera', 'Dashboard')
    if not Dashboard.objects.filter(dashboard_id='cartera').exists():
        Dashboard.objects.create(dashboard_id='cartera', name='Dashboard de cartera', area='Cartera')


def no_revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cartera', '0004_agregar_modelo_dashboard'),
    ]

    operations = [
        migrations.RunPython(sembrar_dashboard_cartera, no_revertir),
    ]
