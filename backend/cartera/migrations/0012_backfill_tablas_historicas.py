"""Agrega Tabla 4 y Tabla 5 (posiciones históricas nuevas, ver `services/plantilla.py`) a los
dashboards que ya estaban sembrados con la plantilla fija ANTES de este cambio — agregar los slots
a `PLANTILLA_SLOTS` no alcanza para que aparezcan solos: un `DashboardLayout` ya existente solo se
reescribe completo al aplicar un mapeo nuevo o "Restablecer al patrón Z"
(`services/dashboard_layout.py::_escribir_componentes`). No destructiva ni duplicable: solo agrega
`tabla-4`/`tabla-5` a los layouts que ya tienen `tabla-3` (es decir, ya fueron sembrados con la
plantilla) y que todavía no las tienen."""

from django.db import migrations

# Mismo contenido ficticio que `services/plantilla.py::datos_ficticios()` para 'tabla-4'/'tabla-5'
# al momento de este cambio — copiado inline (no se importa código de la app desde una migración)
# para que esta migración siga produciendo el mismo resultado aunque el ficticio cambie después.
_CONTENIDO_FICTICIO = {
    'tabla-4': {
        'titulo': 'Tabla 4', 'descripcion': 'Ejemplo: detalle por canal de venta.',
        'columnas': ['Canal', 'Ventas (USD)', 'Unidades', '% del total'],
        'filas': [
            ['Tienda física', 320000, '1,540', 43.0],
            ['E-commerce', 250000, '1,180', 33.6],
            ['Marketplace', 175000, '820', 23.5],
        ],
        'total': ['Total', 745000, '3,540', 100.0],
    },
    'tabla-5': {
        'titulo': 'Tabla 5', 'descripcion': 'Ejemplo: detalle por mes.',
        'columnas': ['Mes', 'Ventas (USD)', 'Unidades', '% del total'],
        'filas': [
            ['Enero', 120000, '600', 16.1],
            ['Febrero', 135000, '650', 18.1],
            ['Marzo', 150000, '700', 20.1],
            ['Abril', 170000, '780', 22.8],
            ['Mayo', 170000, '810', 22.8],
        ],
        'total': ['Total', 745000, '3,540', 100.0],
    },
}
TABLA_MEDIA_ANCHO, TABLA_MEDIA_ALTO = 6, 340


def agregar_tablas_historicas(apps, schema_editor):
    DashboardLayout = apps.get_model('cartera', 'DashboardLayout')
    DashboardComponent = apps.get_model('cartera', 'DashboardComponent')

    layouts_con_tabla_3 = DashboardLayout.objects.filter(
        components__component_id='tabla-3',
    ).exclude(components__component_id='tabla-4').distinct()

    for layout in layouts_con_tabla_3:
        orden_maximo = layout.components.order_by('-order').values_list('order', flat=True).first() or 0
        nuevos = [
            DashboardComponent(
                layout=layout, component_id=component_id, type='chart', chart_type='tabla',
                row=1, order=orden_maximo + indice, width=TABLA_MEDIA_ANCHO, height=TABLA_MEDIA_ALTO,
                is_visible=True, content=_CONTENIDO_FICTICIO[component_id], styles={}, config={}, mapeo={},
            )
            for indice, component_id in enumerate(('tabla-4', 'tabla-5'), start=1)
        ]
        DashboardComponent.objects.bulk_create(nuevos)


def no_revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('cartera', '0011_cargaarchivo_subido_por'),
    ]

    operations = [
        migrations.RunPython(agregar_tablas_historicas, no_revertir),
    ]
