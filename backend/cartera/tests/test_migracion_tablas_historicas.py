"""Migración de datos `0012_backfill_tablas_historicas`: agrega Tabla 4/Tabla 5 a los dashboards
que ya estaban sembrados con la plantilla fija (13 posiciones, antes de este cambio) — sin este
backfill, esos dashboards nunca mostrarían las posiciones históricas nuevas hasta la próxima vez
que se les aplique un mapeo o se restablezca el patrón Z (`services/dashboard_layout.py`)."""

from importlib import import_module

from django.apps import apps
from django.test import TestCase

from cartera.models import DashboardComponent, DashboardLayout

_migracion = import_module('cartera.migrations.0012_backfill_tablas_historicas')

_IDS_PLANTILLA_VIEJA = (
    'kpi-1', 'kpi-2', 'kpi-3', 'kpi-4',
    'grafico-3', 'grafico-1', 'grafico-2', 'grafico-4', 'grafico-5', 'grafico-6',
    'tabla-1', 'tabla-2', 'tabla-3',
)


def _sembrar_plantilla_vieja(dashboard_id):
    """Simula un dashboard sembrado ANTES de este cambio: 13 componentes, sin tabla-4/tabla-5."""
    layout = DashboardLayout.objects.create(dashboard_id=dashboard_id)
    DashboardComponent.objects.bulk_create([
        DashboardComponent(
            layout=layout, component_id=component_id, type='chart', chart_type='tabla' if component_id.startswith('tabla') else '',
            row=1, order=indice, width=6, height=340, is_visible=True, content={}, styles={}, config={}, mapeo={},
        )
        for indice, component_id in enumerate(_IDS_PLANTILLA_VIEJA, start=1)
    ])
    return layout


class BackfillTablasHistoricasTests(TestCase):
    def test_agrega_tabla_4_y_tabla_5_a_un_dashboard_ya_sembrado(self):
        layout = _sembrar_plantilla_vieja('finanzas')

        _migracion.agregar_tablas_historicas(apps, None)

        componentes = {c.component_id: c for c in layout.components.all()}
        self.assertIn('tabla-4', componentes)
        self.assertIn('tabla-5', componentes)
        self.assertEqual(componentes['tabla-4'].order, 14)
        self.assertEqual(componentes['tabla-5'].order, 15)
        self.assertEqual(componentes['tabla-4'].chart_type, 'tabla')
        self.assertEqual(componentes['tabla-4'].content['titulo'], 'Tabla 4')
        self.assertEqual(componentes['tabla-5'].content['titulo'], 'Tabla 5')

    def test_correrla_dos_veces_no_duplica(self):
        _sembrar_plantilla_vieja('finanzas')

        _migracion.agregar_tablas_historicas(apps, None)
        _migracion.agregar_tablas_historicas(apps, None)

        total_tabla_4 = DashboardComponent.objects.filter(layout__dashboard_id='finanzas', component_id='tabla-4').count()
        self.assertEqual(total_tabla_4, 1)

    def test_no_toca_un_dashboard_que_nunca_tuvo_la_plantilla(self):
        layout = DashboardLayout.objects.create(dashboard_id='vacio')

        _migracion.agregar_tablas_historicas(apps, None)

        self.assertEqual(layout.components.count(), 0)
