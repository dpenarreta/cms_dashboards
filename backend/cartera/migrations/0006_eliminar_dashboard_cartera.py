"""Elimina el dashboard 'cartera' sembrado por `0005_seed_dashboard_cartera.py`: ya no existe un
dashboard especial con un pipeline de KPIs propio (`cartera/services/dashboard_layout.py` ahora
aplica el mismo layout por defecto a cualquier dashboard) — un administrador puede crear cualquier
dashboard por área y todos alojan el mismo pipeline. Se eliminan también, en cascada, sus cargas
de archivo y su layout guardado, igual que al eliminar cualquier otro dashboard desde el CRUD
(`cartera/services/dashboards.py::eliminar_dashboard`)."""

from django.db import migrations

DASHBOARD_ID = 'cartera'


def eliminar_dashboard_cartera(apps, schema_editor):
    Dashboard = apps.get_model('cartera', 'Dashboard')
    CargaArchivo = apps.get_model('cartera', 'CargaArchivo')
    DashboardLayout = apps.get_model('cartera', 'DashboardLayout')

    CargaArchivo.objects.filter(dashboard_id=DASHBOARD_ID).delete()
    DashboardLayout.objects.filter(dashboard_id=DASHBOARD_ID).delete()
    Dashboard.objects.filter(dashboard_id=DASHBOARD_ID).delete()


def no_revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cartera', '0005_seed_dashboard_cartera'),
    ]

    operations = [
        migrations.RunPython(eliminar_dashboard_cartera, no_revertir),
    ]
