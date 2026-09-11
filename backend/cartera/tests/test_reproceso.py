"""Reproceso del contenido almacenado de dashboards existentes.

Lo que más importa verificar acá no es que el contenido se recalcule, sino que al recalcularlo NO
se pierda la personalización visual. `plantilla.aplicar_mapeo` — el camino obvio para "recalcular"
— borra y recrea los componentes, así que ancho, alto, colores y tipo de gráfico vuelven a los
valores de fábrica. `reproceso` existe precisamente para no hacer eso.
"""

import uuid

import pandas as pd
from django.conf import settings
from django.test import TestCase

from cartera.models import CargaArchivo, DashboardComponent, DashboardLayout
from cartera.services import dashboard_layout, generic_charts, plantilla, reproceso
from cartera.utils.archivos import asegurar_directorio

DASHBOARD = 'reproceso-test'


def _df():
    return pd.DataFrame({
        'Cliente': ['ana', 'beto', 'caro', 'ana'],
        'Zona': ['norte', 'sur', 'norte', 'sur'],
        'Saldo': [100.0, 250.0, 50.0, 75.0],
    })


class ReprocesoTests(TestCase):
    def setUp(self):
        self.df = _df()
        self.carga = CargaArchivo.objects.create(
            id=uuid.uuid4(), dashboard_id=DASHBOARD, nombre_original='datos.xlsx',
            estado=CargaArchivo.Estado.PROCESADO,
        )
        nombre = f'{self.carga.id}.xlsx'
        ruta = asegurar_directorio(settings.CARTERA_ARCHIVOS_DIR) / nombre
        self.df.to_excel(ruta, index=False, sheet_name='Datos')
        self.carga.archivo_permanente_nombre = nombre
        self.carga.save(update_fields=['archivo_permanente_nombre'])

        columnas = generic_charts.analizar_columnas(self.df)['columnas']
        mapeo = plantilla.sugerir_mapeo(columnas)
        plantilla.aplicar_mapeo(DASHBOARD, self.df, mapeo)
        self.layout = dashboard_layout.obtener_o_crear_layout(DASHBOARD)

    def _un_componente_con_mapeo(self):
        return self.layout.components.exclude(mapeo={}).exclude(content={}).first()

    def test_analizar_no_escribe_nada(self):
        componente = self._un_componente_con_mapeo()
        DashboardComponent.objects.filter(pk=componente.pk).update(content={'titulo': 'valor viejo'})
        version_antes = DashboardLayout.objects.get(pk=self.layout.pk).version

        resultado = reproceso.analizar_dashboard(DASHBOARD)

        self.assertTrue(resultado['ok'])
        self.assertTrue(resultado['cambios'])
        self.assertEqual(DashboardComponent.objects.get(pk=componente.pk).content, {'titulo': 'valor viejo'})
        self.assertEqual(DashboardLayout.objects.get(pk=self.layout.pk).version, version_antes)

    def test_aplicar_actualiza_el_contenido(self):
        componente = self._un_componente_con_mapeo()
        contenido_correcto = componente.content
        DashboardComponent.objects.filter(pk=componente.pk).update(content={'titulo': 'valor viejo'})

        reproceso.aplicar_dashboard(DASHBOARD)

        self.assertEqual(DashboardComponent.objects.get(pk=componente.pk).content, contenido_correcto)

    def test_aplicar_conserva_la_personalizacion_visual(self):
        """La razón de ser de este módulo: `aplicar_mapeo` pisaría todo esto."""
        componente = self._un_componente_con_mapeo()
        DashboardComponent.objects.filter(pk=componente.pk).update(
            content={'titulo': 'valor viejo'}, width=2, height=999,
            styles={'colorPrincipal': '#123456'}, chart_type='line',
        )

        reproceso.aplicar_dashboard(DASHBOARD)

        despues = DashboardComponent.objects.get(pk=componente.pk)
        self.assertEqual(despues.width, 2)
        self.assertEqual(despues.height, 999)
        self.assertEqual(despues.styles, {'colorPrincipal': '#123456'})
        self.assertEqual(despues.chart_type, 'line')

    def test_aplicar_sube_la_version_del_layout(self):
        componente = self._un_componente_con_mapeo()
        DashboardComponent.objects.filter(pk=componente.pk).update(content={'titulo': 'valor viejo'})
        version_antes = DashboardLayout.objects.get(pk=self.layout.pk).version

        reproceso.aplicar_dashboard(DASHBOARD)

        self.assertEqual(DashboardLayout.objects.get(pk=self.layout.pk).version, version_antes + 1)

    def test_sin_cambios_no_sube_la_version(self):
        version_antes = DashboardLayout.objects.get(pk=self.layout.pk).version

        resultado = reproceso.aplicar_dashboard(DASHBOARD)

        self.assertEqual(resultado['cambios'], [])
        self.assertEqual(DashboardLayout.objects.get(pk=self.layout.pk).version, version_antes)

    def test_es_idempotente(self):
        componente = self._un_componente_con_mapeo()
        DashboardComponent.objects.filter(pk=componente.pk).update(content={'titulo': 'valor viejo'})

        primera = reproceso.aplicar_dashboard(DASHBOARD)
        segunda = reproceso.aplicar_dashboard(DASHBOARD)

        self.assertTrue(primera['cambios'])
        self.assertEqual(segunda['cambios'], [])

    def test_omite_un_dashboard_sin_carga_procesada(self):
        self.carga.estado = CargaArchivo.Estado.SUBIDO
        self.carga.save(update_fields=['estado'])

        resultado = reproceso.analizar_dashboard(DASHBOARD)

        self.assertFalse(resultado['ok'])
        self.assertIn('carga procesada', resultado['motivo'])

    def test_omite_un_dashboard_sin_mapeo(self):
        plantilla.sembrar_plantilla('sin-mapeo')

        resultado = reproceso.analizar_dashboard('sin-mapeo')

        self.assertFalse(resultado['ok'])
        self.assertIn('mapeo', resultado['motivo'])

    def test_omite_un_dashboard_sin_layout(self):
        resultado = reproceso.analizar_dashboard('no-existe')

        self.assertFalse(resultado['ok'])
        self.assertIn('layout', resultado['motivo'])

    def test_omite_cuando_el_archivo_ya_no_esta_en_disco(self):
        self.carga.archivo_permanente_nombre = 'no-existe.xlsx'
        self.carga.archivo_temp_nombre = ''
        self.carga.save(update_fields=['archivo_permanente_nombre', 'archivo_temp_nombre'])

        resultado = reproceso.analizar_dashboard(DASHBOARD)

        self.assertFalse(resultado['ok'])
        self.assertIn('No se pudo leer', resultado['motivo'])

    def test_dashboards_con_layout_los_lista(self):
        self.assertIn(DASHBOARD, reproceso.dashboards_con_layout())
