"""Elimina Tabla 4 y Tabla 5 (posiciones históricas, ver `services/plantilla.py`) de TODOS los
dashboards que ya las tenían — se quitaron de `PLANTILLA_SLOTS` porque Tabla 3 pasa a cumplir ese
mismo rol (la zona de tablas de apoyo queda en Tabla 2 normal + Tabla 3 histórica, sin necesidad
de dos posiciones históricas duplicadas que además mostraban exactamente el mismo contenido, ver
`DashboardAreaPage.jsx`). Igual que la migración 0012 que las agregó, esto no toca componentes de
Zona Personal (`config.zona == 'personal'`) ni ningún otro componente — solo borra las dos
posiciones fijas por su `component_id`, en cualquier layout que las tenga (dashboards reales y la
plantilla base). Tabla 3 no se toca acá: pasa a comportarse como histórica solo por el cambio de
código en el frontend (`component_id === 'tabla-3'`), sin necesitar ningún dato distinto.

Bump de `version` en cada layout tocado para que un editor con la página ya abierta reciba el
aviso de conflicto (409, ver `.claude/rules/dashboards.md`) en vez de sobrescribir en silencio la
próxima vez que guarde."""

from django.db import migrations


def eliminar_tablas_4_y_5(apps, schema_editor):
    DashboardLayout = apps.get_model('cartera', 'DashboardLayout')
    DashboardComponent = apps.get_model('cartera', 'DashboardComponent')

    layouts_afectados = DashboardLayout.objects.filter(
        components__component_id__in=('tabla-4', 'tabla-5'),
    ).distinct()

    for layout in layouts_afectados:
        DashboardComponent.objects.filter(layout=layout, component_id__in=('tabla-4', 'tabla-5')).delete()
        layout.version += 1
        layout.save(update_fields=['version', 'actualizado_en'])


def no_revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cartera', '0013_columnahistorica'),
    ]

    operations = [
        migrations.RunPython(eliminar_tablas_4_y_5, no_revertir),
    ]
