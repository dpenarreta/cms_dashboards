"""Migración de datos `0021_sembrar_cartera_dashboard_directorio`: siembra la réplica de la
pestaña "6. Cartera" del mockup (4 KPI, antigüedad por tramos, cumplimiento de metas,
concentración) en `dashboard-directorio`, todos bloqueados (`config.bloqueado=True`), y oculta +
bloquea las 13 posiciones de fábrica de la plantilla — ver docstring de la propia migración para
el detalle completo."""

from importlib import import_module

from django.apps import apps
from django.test import TestCase

from cartera.models import Dashboard, DashboardComponent, DashboardLayout

_migracion = import_module('cartera.migrations.0021_sembrar_cartera_dashboard_directorio')

_IDS_NUEVOS = (
    'cartera-total', 'al-corriente', 'vencida-total', 'vencida-mas-120-dias',
    'antiguedad-de-cartera', 'cumplimiento-metas-antiguedad', 'concentracion-de-cartera',
)


def _sembrar_plantilla_de_fabrica(dashboard_id):
    """Simula el estado de un dashboard recién creado: 13 posiciones de fábrica, visibles y sin
    bloquear — el mismo estado en el que nace cualquier dashboard hoy (`sembrar_plantilla_desde_base`)."""
    layout = DashboardLayout.objects.create(dashboard_id=dashboard_id)
    DashboardComponent.objects.bulk_create([
        DashboardComponent(
            layout=layout, component_id=component_id, type='chart', chart_type='tabla' if component_id.startswith('tabla') else '',
            row=1, order=indice, width=6, height=340, is_visible=True, content={}, styles={}, config={}, mapeo={},
        )
        for indice, component_id in enumerate(_migracion.IDS_FABRICA, start=1)
    ])
    return layout


class SembrarCarteraDashboardDirectorioTests(TestCase):
    def setUp(self):
        Dashboard.objects.create(dashboard_id='dashboard-directorio', name='Dashboard Directorio')
        self.layout = _sembrar_plantilla_de_fabrica('dashboard-directorio')

    def test_agrega_los_7_componentes_nuevos_bloqueados(self):
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        componentes = {c.component_id: c for c in self.layout.components.all()}
        for component_id in _IDS_NUEVOS:
            self.assertIn(component_id, componentes)
            self.assertTrue(componentes[component_id].config.get('bloqueado'))
            self.assertTrue(componentes[component_id].is_visible)

    def test_oculta_y_bloquea_las_13_posiciones_de_fabrica(self):
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        componentes = {c.component_id: c for c in self.layout.components.all()}
        for component_id in _migracion.IDS_FABRICA:
            self.assertFalse(componentes[component_id].is_visible, component_id)
            self.assertTrue(componentes[component_id].config.get('bloqueado'), component_id)

    def test_los_4_kpi_tienen_el_mapeo_esperado(self):
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        componentes = {c.component_id: c for c in self.layout.components.all()}
        self.assertEqual(componentes['cartera-total'].mapeo, {
            'disponible': True, 'calculo': 'kpi', 'columna_valor': 'Saldo', 'formato': 'moneda',
        })
        self.assertEqual(componentes['al-corriente'].mapeo, {
            'disponible': True, 'calculo': 'kpi', 'columna_valor': 'Saldo', 'formato': 'moneda',
            'columna_filtro': 'Fecha de Vencimiento', 'tipo_filtro': 'dias_vencidos',
            'operador_filtro': 'menor_igual', 'dias_filtro': 0,
        })
        self.assertEqual(componentes['vencida-total'].mapeo['operador_filtro'], 'mayor')
        self.assertEqual(componentes['vencida-total'].mapeo['dias_filtro'], 0)
        self.assertEqual(componentes['vencida-mas-120-dias'].mapeo['dias_filtro'], 120)

    def test_los_4_kpi_tienen_un_color_de_acento_distinto(self):
        """Alcance confirmado con el usuario: solo colores/acentos por componente, usando el
        mismo mecanismo que ya existe (`styles.colorPrincipal`, `GenericKpiCard.jsx`) — sin tocar
        el diseño/estructura visual de los componentes genéricos en sí."""
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        componentes = {c.component_id: c for c in self.layout.components.all()}
        colores = {cid: componentes[cid].styles.get('colorPrincipal') for cid in (
            'cartera-total', 'al-corriente', 'vencida-total', 'vencida-mas-120-dias',
        )}
        self.assertTrue(all(colores.values()))
        self.assertEqual(len(set(colores.values())), 4)  # los 4 son distintos entre sí

    def test_el_grafico_de_antiguedad_tiene_un_color_por_tramo(self):
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        componente = DashboardComponent.objects.get(layout=self.layout, component_id='antiguedad-de-cartera')
        colores_por_tramo = componente.styles.get('coloresPorCategoria', {})
        self.assertEqual(set(colores_por_tramo.keys()), set(_migracion._TRAMOS_ANTIGUEDAD))
        self.assertEqual(len(set(colores_por_tramo.values())), 6)  # los 6 son distintos entre sí

    def test_tramos_cumplimiento_y_concentracion_tienen_el_mapeo_esperado(self):
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        componentes = {c.component_id: c for c in self.layout.components.all()}
        self.assertEqual(componentes['antiguedad-de-cartera'].mapeo, {
            'disponible': True, 'calculo': 'tramos_antiguedad',
            'columna_fecha': 'Fecha de Vencimiento', 'columna_valor': 'Saldo',
        })
        mapeo_cumplimiento = componentes['cumplimiento-metas-antiguedad'].mapeo
        self.assertEqual(mapeo_cumplimiento['calculo'], 'cumplimiento_metas')
        self.assertEqual(len(mapeo_cumplimiento['metas']), 6)
        self.assertEqual(componentes['concentracion-de-cartera'].mapeo, {
            'disponible': True, 'calculo': 'concentracion',
            'columna_id': 'Cliente', 'columna_valor': 'Saldo', 'top_n': 16,
        })

    def test_la_fila_de_mas_de_120_dias_no_esta_forzada_al_100_por_ciento(self):
        """Regresión: la fila 6 de "cumplimiento_metas" es el tramo de cola sola, no un cierre al
        100% del archivo — ver la corrección de `generic_charts.py::generar_datos_cumplimiento_tramos`."""
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        componente = DashboardComponent.objects.get(layout=self.layout, component_id='cumplimiento-metas-antiguedad')
        ultima_fila = componente.content['filas'][-1]
        self.assertEqual(ultima_fila[0], 'Más de 120 días')
        self.assertNotEqual(ultima_fila[2], 100.0)

    def test_correrla_dos_veces_no_duplica(self):
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        total = DashboardComponent.objects.filter(layout=self.layout, component_id='cartera-total').count()
        self.assertEqual(total, 1)

    def test_no_toca_nada_si_el_dashboard_no_existe(self):
        Dashboard.objects.filter(dashboard_id='dashboard-directorio').delete()

        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        self.assertEqual(self.layout.components.filter(component_id='cartera-total').count(), 0)

    def test_revertir_deja_el_dashboard_como_estaba_antes(self):
        _migracion.sembrar_cartera_dashboard_directorio(apps, None)

        _migracion.revertir(apps, None)

        componentes = {c.component_id: c for c in self.layout.components.all()}
        for component_id in _IDS_NUEVOS:
            self.assertNotIn(component_id, componentes)
        for component_id in _migracion.IDS_FABRICA:
            self.assertTrue(componentes[component_id].is_visible, component_id)
            self.assertNotIn('bloqueado', componentes[component_id].config, component_id)
