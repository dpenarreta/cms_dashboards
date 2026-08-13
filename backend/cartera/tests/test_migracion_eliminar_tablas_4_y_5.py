"""Migración de datos `0014_eliminar_tablas_4_y_5`: quita Tabla 4/Tabla 5 de los dashboards que ya
las tenían — se sacaron de `PLANTILLA_SLOTS` porque Tabla 3 pasa a cumplir ese mismo rol (ver
`services/plantilla.py`). No toca Zona Personal ni ningún otro componente, y bumpea `version` en
cada layout tocado para que un editor con la página abierta reciba el 409 de conflicto."""

from importlib import import_module

from django.apps import apps
from django.test import TestCase

from cartera.models import DashboardComponent, DashboardLayout

_migracion = import_module('cartera.migrations.0014_eliminar_tablas_4_y_5')

_IDS_PLANTILLA_VIEJA = (
    'kpi-1', 'kpi-2', 'kpi-3', 'kpi-4',
    'grafico-3', 'grafico-1', 'grafico-2', 'grafico-4', 'grafico-5', 'grafico-6',
    'tabla-1', 'tabla-2', 'tabla-3', 'tabla-4', 'tabla-5',
)


def _sembrar_plantilla_vieja(dashboard_id, version=1):
    """Simula un dashboard sembrado ANTES de este cambio: 15 componentes, con tabla-4/tabla-5."""
    layout = DashboardLayout.objects.create(dashboard_id=dashboard_id, version=version)
    DashboardComponent.objects.bulk_create([
        DashboardComponent(
            layout=layout, component_id=component_id, type='chart', chart_type='tabla' if component_id.startswith('tabla') else '',
            row=1, order=indice, width=6, height=340, is_visible=True, content={}, styles={}, config={}, mapeo={},
        )
        for indice, component_id in enumerate(_IDS_PLANTILLA_VIEJA, start=1)
    ])
    return layout


class EliminarTablas4Y5Tests(TestCase):
    def test_elimina_tabla_4_y_tabla_5_de_un_dashboard_que_las_tenia(self):
        layout = _sembrar_plantilla_vieja('finanzas')

        _migracion.eliminar_tablas_4_y_5(apps, None)

        componentes = {c.component_id for c in layout.components.all()}
        self.assertNotIn('tabla-4', componentes)
        self.assertNotIn('tabla-5', componentes)
        self.assertIn('tabla-3', componentes)
        self.assertEqual(componentes, set(_IDS_PLANTILLA_VIEJA) - {'tabla-4', 'tabla-5'})

    def test_bumpea_la_version_del_layout_tocado(self):
        layout = _sembrar_plantilla_vieja('finanzas', version=3)

        _migracion.eliminar_tablas_4_y_5(apps, None)

        layout.refresh_from_db()
        self.assertEqual(layout.version, 4)

    def test_no_toca_un_dashboard_que_nunca_tuvo_tabla_4_o_tabla_5(self):
        layout = DashboardLayout.objects.create(dashboard_id='sin-historicas', version=2)
        DashboardComponent.objects.create(
            layout=layout, component_id='tabla-3', type='chart', chart_type='tabla',
            row=1, order=13, width=6, height=340, is_visible=True, content={}, styles={}, config={}, mapeo={},
        )

        _migracion.eliminar_tablas_4_y_5(apps, None)

        layout.refresh_from_db()
        self.assertEqual(layout.version, 2)
        self.assertTrue(layout.components.filter(component_id='tabla-3').exists())

    def test_no_toca_componentes_de_zona_personal(self):
        layout = _sembrar_plantilla_vieja('finanzas')
        DashboardComponent.objects.create(
            layout=layout, component_id='mi-kpi-personal', type='kpi', chart_type='',
            row=1, order=16, width=3, height=180, is_visible=True, content={}, styles={},
            config={'zona': 'personal'}, mapeo={},
        )

        _migracion.eliminar_tablas_4_y_5(apps, None)

        self.assertTrue(layout.components.filter(component_id='mi-kpi-personal').exists())

    def test_correrla_dos_veces_no_hace_nada_la_segunda_vez(self):
        layout = _sembrar_plantilla_vieja('finanzas')

        _migracion.eliminar_tablas_4_y_5(apps, None)
        layout.refresh_from_db()
        version_tras_primera = layout.version

        _migracion.eliminar_tablas_4_y_5(apps, None)
        layout.refresh_from_db()

        self.assertEqual(layout.version, version_tras_primera)
