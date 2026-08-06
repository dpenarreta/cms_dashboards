"""Plantilla fija de dashboard (`services/plantilla.py`): siembra al crear un dashboard, mapeo
automático de columnas de un archivo a las 13 posiciones fijas, y aplicación de ese mapeo."""

import os

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from cartera.models import CargaArchivo, Dashboard, DashboardComponent, FilaArchivoHistorico
from cartera.services import plantilla

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'cartera_ejemplo.xlsx')
User = get_user_model()


class SembrarPlantillaServiceTests(TestCase):
    def test_crea_las_13_posiciones_con_ids_fijos(self):
        plantilla.sembrar_plantilla('finanzas')
        componentes = {c.component_id: c for c in DashboardComponent.objects.filter(layout__dashboard_id='finanzas')}
        self.assertEqual(set(componentes.keys()), {slot['id'] for slot in plantilla.PLANTILLA_SLOTS})

    def test_los_kpi_traen_icono_y_color_fijos(self):
        plantilla.sembrar_plantilla('finanzas')
        kpi_1 = DashboardComponent.objects.get(layout__dashboard_id='finanzas', component_id='kpi-1')
        self.assertEqual(kpi_1.config['icono'], 'persona')
        self.assertEqual(kpi_1.styles['colorPrincipal'], '#2a78d6')

    def test_los_tipos_con_leyenda_traen_posicion_de_leyenda_por_defecto(self):
        plantilla.sembrar_plantilla('finanzas')
        grafico_3 = DashboardComponent.objects.get(layout__dashboard_id='finanzas', component_id='grafico-3')
        self.assertEqual(grafico_3.chart_type, 'area_apilada')
        self.assertEqual(grafico_3.config['leyenda_posicion'], 'abajo')

    def test_sembrar_dos_veces_no_duplica_componentes(self):
        plantilla.sembrar_plantilla('finanzas')
        plantilla.sembrar_plantilla('finanzas')
        total = DashboardComponent.objects.filter(layout__dashboard_id='finanzas').count()
        self.assertEqual(total, len(plantilla.PLANTILLA_SLOTS))

    def test_preserva_los_componentes_de_zona_personal_al_volver_a_sembrar(self):
        from cartera.services import dashboard_layout as dl
        plantilla.sembrar_plantilla('finanzas')
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Mi KPI', 'columna_valor': 'x', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 42.0}, 'zona': 'personal',
        })

        plantilla.sembrar_plantilla('finanzas')

        componentes = DashboardComponent.objects.filter(layout__dashboard_id='finanzas')
        self.assertEqual(componentes.count(), len(plantilla.PLANTILLA_SLOTS) + 1)
        personal = componentes.get(component_id='mi-kpi')
        self.assertEqual(personal.content['valor'], 42.0)
        self.assertEqual(personal.config['zona'], 'personal')
        self.assertEqual(personal.order, len(plantilla.PLANTILLA_SLOTS) + 1)


class SugerirMapeoServiceTests(TestCase):
    def _columnas(self, df):
        from cartera.services import generic_charts
        return generic_charts.analizar_columnas(df)['columnas']

    def test_con_columnas_suficientes_todas_las_posiciones_quedan_disponibles(self):
        # tabla-3 necesita 3 columnas de categoría distintas -> el archivo trae 3 (región,
        # vendedor, producto) para que ninguna de las 13 posiciones caiga al dato ficticio.
        df = pd.DataFrame({
            'region': ['Norte', 'Sur', 'Centro', 'Norte', 'Sur'],
            'vendedor': ['A', 'B', 'A', 'B', 'A'],
            'producto': ['X', 'Y', 'X', 'Z', 'Y'],
            'ventas': [100, 200, 150, 50, 300],
            'costo': [50, 100, 75, 25, 150],
        })
        mapeo = plantilla.sugerir_mapeo(self._columnas(df))
        self.assertTrue(all(m['disponible'] for m in mapeo.values()), mapeo)

    def test_sin_columnas_categoricas_solo_los_kpi_quedan_disponibles(self):
        df = pd.DataFrame({'ventas': [100, 200, 150], 'costo': [50, 100, 75]})
        mapeo = plantilla.sugerir_mapeo(self._columnas(df))
        for i in range(1, 5):
            self.assertTrue(mapeo[f'kpi-{i}']['disponible'])
        for slot_id in ('grafico-1', 'grafico-3', 'tabla-1'):
            self.assertFalse(mapeo[slot_id]['disponible'])

    def test_es_deterministico(self):
        df = pd.DataFrame({
            'region': ['Norte', 'Sur', 'Centro'], 'ventas': [100, 200, 150], 'costo': [50, 100, 75],
        })
        columnas = self._columnas(df)
        self.assertEqual(plantilla.sugerir_mapeo(columnas), plantilla.sugerir_mapeo(columnas))

    def test_las_columnas_de_valor_de_tabla_traen_tipo_de_agregacion_suma_por_defecto(self):
        df = pd.DataFrame({
            'region': ['Norte', 'Sur', 'Centro'], 'ventas': [100, 200, 150], 'costo': [50, 100, 75],
        })
        mapeo = plantilla.sugerir_mapeo(self._columnas(df))
        for entrada in mapeo['tabla-1']['columnas_valor']:
            self.assertEqual(entrada, {'columna': entrada['columna'], 'tipo_agregacion': 'suma'})

    def test_incluye_el_chart_type_por_defecto_de_cada_grafico(self):
        df = pd.DataFrame({
            'region': ['Norte', 'Sur', 'Centro'], 'ventas': [100, 200, 150], 'costo': [50, 100, 75],
        })
        mapeo = plantilla.sugerir_mapeo(self._columnas(df))
        self.assertEqual(mapeo['grafico-1']['chart_type'], 'barras_verticales')
        self.assertEqual(mapeo['grafico-2']['chart_type'], 'lineas_multiples')
        self.assertEqual(mapeo['grafico-3']['chart_type'], 'area_apilada')
        self.assertEqual(mapeo['grafico-4']['chart_type'], 'dona')
        self.assertEqual(mapeo['grafico-5']['chart_type'], 'pastel')


class CalcularDatosMapeoServiceTests(TestCase):
    def test_una_posicion_disponible_usa_datos_reales(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur', 'Norte'], 'ventas': [100, 200, 50]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'ventas'}}
        # El resto de posiciones no vienen en el mapeo -> caen al dato ficticio.
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1']['valor'], 350.0)
        self.assertNotIn('tendencia', datos['kpi-1'])
        self.assertEqual(datos['kpi-2'], plantilla.datos_ficticios()['kpi-2'])

    def test_columna_inexistente_cae_al_dato_ficticio(self):
        df = pd.DataFrame({'ventas': [100, 200]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'no_existe'}}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1'], plantilla.datos_ficticios()['kpi-1'])

    def test_kpi_con_tipo_agregacion_conteo_unicos_cuenta_valores_distintos(self):
        df = pd.DataFrame({'cliente': ['Ana', 'Ana', 'Luis', 'Carlos']})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'cliente', 'tipo_agregacion': 'conteo_unicos'}}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1']['valor'], 3)
        self.assertIn('Cantidad de valores únicos', datos['kpi-1']['descripcion'])

    def test_kpi_con_tipo_agregacion_promedio_calcula_la_media(self):
        df = pd.DataFrame({'saldo': [100, 200, 300]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'saldo', 'tipo_agregacion': 'promedio'}}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1']['valor'], 200.0)
        self.assertIn('Promedio de', datos['kpi-1']['descripcion'])

    def test_kpi_con_tipo_agregacion_promedio_ignora_valores_no_numericos(self):
        df = pd.DataFrame({'saldo': [100, 'no numérico', 300]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'saldo', 'tipo_agregacion': 'promedio'}}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1']['valor'], 200.0)

    def test_kpi_sin_tipo_agregacion_sigue_sumando_por_defecto(self):
        df = pd.DataFrame({'ventas': [100, 200, 50]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'ventas'}}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1']['valor'], 350.0)
        self.assertIn('Suma de', datos['kpi-1']['descripcion'])

    def test_kpi_con_filtro_solo_suma_las_filas_que_coinciden(self):
        df = pd.DataFrame({
            'saldo': [100, 200, 50, 300],
            'causal': ['GESTIONANDO', 'PAGADO', 'GESTIONANDO', 'PAGADO'],
        })
        mapeo = {'kpi-1': {
            'disponible': True, 'columna_valor': 'saldo',
            'columna_filtro': 'causal', 'valor_filtro': 'GESTIONANDO',
        }}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1']['valor'], 150.0)
        self.assertIn('donde "causal" = "GESTIONANDO"', datos['kpi-1']['descripcion'])

    def test_filtro_aplica_igual_a_una_grafica_no_solo_a_un_kpi(self):
        df = pd.DataFrame({
            'ventas': [100, 200, 50, 300],
            'region': ['Norte', 'Norte', 'Sur', 'Sur'],
            'causal': ['GESTIONANDO', 'PAGADO', 'GESTIONANDO', 'PAGADO'],
        })
        mapeo = {'grafico-1': {
            'disponible': True, 'columna_categoria': 'region', 'columna_valor': 'ventas',
            'columna_filtro': 'causal', 'valor_filtro': 'GESTIONANDO',
        }}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(dict(zip(datos['grafico-1']['categorias'], datos['grafico-1']['valores'])), {'Norte': 100.0, 'Sur': 50.0})

    def test_filtro_sin_coincidencias_da_un_resultado_real_en_cero_no_el_dato_ficticio(self):
        df = pd.DataFrame({'saldo': [100, 200], 'causal': ['PAGADO', 'PAGADO']})
        mapeo = {'kpi-1': {
            'disponible': True, 'columna_valor': 'saldo', 'columna_filtro': 'causal', 'valor_filtro': 'GESTIONANDO',
        }}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1']['valor'], 0.0)
        self.assertNotEqual(datos['kpi-1'], plantilla.datos_ficticios()['kpi-1'])

    def test_columna_de_filtro_inexistente_cae_al_dato_ficticio(self):
        df = pd.DataFrame({'saldo': [100, 200]})
        mapeo = {'kpi-1': {
            'disponible': True, 'columna_valor': 'saldo', 'columna_filtro': 'no_existe', 'valor_filtro': 'X',
        }}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['kpi-1'], plantilla.datos_ficticios()['kpi-1'])

    def test_sin_filtro_elegido_la_descripcion_no_cambia(self):
        df = pd.DataFrame({'saldo': [100, 200]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'saldo'}}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertNotIn('donde', datos['kpi-1']['descripcion'])

    def test_tabla_calcula_columnas_filas_y_total(self):
        df = pd.DataFrame({
            'producto': ['A', 'A', 'B', 'C'],
            'ventas': [100, 50, 80, 60],
        })
        mapeo = {'tabla-1': {'disponible': True, 'columna_id': 'producto', 'columnas_valor': ['ventas']}}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        self.assertEqual(datos['tabla-1']['columnas'], ['producto', 'ventas', '% del total'])
        self.assertEqual(datos['tabla-1']['total'][1], 290.0)

    def test_tabla_respeta_el_tipo_de_agregacion_elegido_por_columna(self):
        df = pd.DataFrame({
            'producto': ['A', 'A', 'B', 'C'],
            'ventas': [100, 50, 80, 60],
        })
        mapeo = {'tabla-1': {
            'disponible': True, 'columna_id': 'producto',
            'columnas_valor': [{'columna': 'ventas', 'tipo_agregacion': 'promedio'}],
        }}
        datos = plantilla.calcular_datos_mapeo(df, mapeo)
        fila_a = next(f for f in datos['tabla-1']['filas'] if f[0] == 'A')
        self.assertEqual(fila_a[1], 75.0)


class AplicarMapeoServiceTests(TestCase):
    def setUp(self):
        self.dashboard_id = 'finanzas'
        plantilla.sembrar_plantilla(self.dashboard_id)

    def test_sobreescribe_las_mismas_13_posiciones_sin_duplicar(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'ventas'}}

        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)

        componentes = DashboardComponent.objects.filter(layout__dashboard_id=self.dashboard_id)
        self.assertEqual(componentes.count(), len(plantilla.PLANTILLA_SLOTS))
        kpi_1 = componentes.get(component_id='kpi-1')
        self.assertEqual(kpi_1.content['valor'], 300.0)

    def test_preserva_los_componentes_de_zona_personal_al_reaplicar_el_mapeo(self):
        """Subir/reaplicar un archivo nuevo no debe borrar la Zona Personal: su contenido se
        preserva tal cual (no se recalcula contra el archivo nuevo, ver docstring de
        `_componentes_zona_personal`)."""
        from cartera.services import dashboard_layout as dl
        dl.agregar_componente_generado(self.dashboard_id, {
            'titulo': 'Mi tabla personal', 'columna_valor': 'x', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 7.0}, 'zona': 'personal',
        })

        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200]})
        plantilla.aplicar_mapeo(self.dashboard_id, df, {'kpi-1': {'disponible': True, 'columna_valor': 'ventas'}})

        componentes = DashboardComponent.objects.filter(layout__dashboard_id=self.dashboard_id)
        self.assertEqual(componentes.count(), len(plantilla.PLANTILLA_SLOTS) + 1)
        personal = componentes.get(component_id='mi-tabla-personal')
        self.assertEqual(personal.content['valor'], 7.0)
        self.assertEqual(personal.order, len(plantilla.PLANTILLA_SLOTS) + 1)

    def test_persiste_el_mapeo_de_cada_posicion_disponible(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200]})
        mapeo = {'kpi-1': {'disponible': True, 'columna_valor': 'ventas', 'tipo_agregacion': 'suma'}}

        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)

        kpi_1 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='kpi-1')
        self.assertEqual(kpi_1.mapeo, mapeo['kpi-1'])
        # Una posición sin mapeo (cae al dato ficticio) no debe quedar con un mapeo fantasma.
        kpi_2 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='kpi-2')
        self.assertEqual(kpi_2.mapeo, {})

    def test_registra_auditoria(self):
        from apps.audit.models import AuditEvent
        usuario = User.objects.create_user(username='ana2', email='ana2@example.com', password='Clave-Segura-123')
        df = pd.DataFrame({'ventas': [1, 2]})
        plantilla.aplicar_mapeo(self.dashboard_id, df, {}, actor=usuario)
        self.assertTrue(AuditEvent.objects.filter(
            domain=AuditEvent.Domain.DASHBOARD_CONFIGURATION, action='DASHBOARD_TEMPLATE_APPLIED',
            actor=usuario, dashboard_id=self.dashboard_id,
        ).exists())

    def test_persiste_el_chart_type_elegido_cuando_es_compatible(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200]})
        mapeo = {'grafico-1': {
            'disponible': True, 'columna_categoria': 'region', 'columna_valor': 'ventas', 'chart_type': 'pastel',
        }}
        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)
        grafico_1 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='grafico-1')
        self.assertEqual(grafico_1.chart_type, 'pastel')
        # 'pastel' necesita leyenda, a diferencia del 'barras_verticales' original del slot.
        self.assertEqual(grafico_1.config['leyenda_posicion'], 'abajo')

    def test_un_chart_type_incompatible_con_el_calculo_cae_al_default_del_slot(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200]})
        mapeo = {'grafico-1': {
            'disponible': True, 'columna_categoria': 'region', 'columna_valor': 'ventas', 'chart_type': 'tabla',
        }}
        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)
        grafico_1 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='grafico-1')
        self.assertEqual(grafico_1.chart_type, 'barras_verticales')

    def test_sin_chart_type_elegido_usa_el_default_del_slot(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200]})
        mapeo = {'grafico-3': {
            'disponible': True, 'columna_categoria': 'region', 'columna_serie': 'region', 'columna_valor': 'ventas',
        }}
        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)
        grafico_3 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='grafico-3')
        self.assertEqual(grafico_3.chart_type, 'area_apilada')

    def test_sembrar_no_se_ve_afectado_por_chart_type_de_un_mapeo_anterior(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200]})
        mapeo = {'grafico-1': {
            'disponible': True, 'columna_categoria': 'region', 'columna_valor': 'ventas', 'chart_type': 'dona',
        }}
        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)
        plantilla.sembrar_plantilla(self.dashboard_id)
        grafico_1 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='grafico-1')
        self.assertEqual(grafico_1.chart_type, 'barras_verticales')

    def test_pastel_dona_son_compatibles_con_multivalor_se_persisten_aunque_el_contenido_siga_siendo_series(self):
        # Antes de esta feature, 'pastel'/'dona' no eran compatibles con 'multivalor' (2+ columnas
        # de valor) y `_chart_type_elegido` los descartaba, cayendo al default del slot — ahora sí
        # se respetan, aunque el contenido calculado siga siendo {categorias, series} (el colapso a
        # una sola porción por categoría lo hace el frontend, no este servicio).
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'ventas': [100, 200], 'costo': [50, 80]})
        mapeo = {'grafico-2': {
            'disponible': True, 'columna_categoria': 'region', 'columnas_valor': ['ventas', 'costo'], 'chart_type': 'pastel',
        }}
        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)
        grafico_2 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='grafico-2')
        self.assertEqual(grafico_2.chart_type, 'pastel')
        self.assertIn('series', grafico_2.content)
        self.assertEqual(grafico_2.config['leyenda_posicion'], 'abajo')

    def test_pastel_dona_son_compatibles_con_multiserie(self):
        df = pd.DataFrame({'region': ['Norte', 'Sur'], 'vendedor': ['Ana', 'Ana'], 'ventas': [100, 200]})
        mapeo = {'grafico-3': {
            'disponible': True, 'columna_categoria': 'region', 'columna_serie': 'vendedor', 'columna_valor': 'ventas',
            'chart_type': 'dona',
        }}
        plantilla.aplicar_mapeo(self.dashboard_id, df, mapeo)
        grafico_3 = DashboardComponent.objects.get(layout__dashboard_id=self.dashboard_id, component_id='grafico-3')
        self.assertEqual(grafico_3.chart_type, 'dona')


class FlujoApiMapeoPlantillaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        usuario = User.objects.create_superuser(username='tester_plantilla', email='tp@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas')
        plantilla.sembrar_plantilla('finanzas')

    def _subir_archivo(self):
        with open(FIXTURE_PATH, 'rb') as f:
            resp = self.client.post('/api/cartera/validar-archivo', {'archivo': f, 'dashboard_id': 'finanzas'}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        return resp.json()['carga_id']

    def test_sugerir_devuelve_mapeo_y_vista_previa(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('mapeo', data)
        self.assertIn('datos', data)
        self.assertEqual(set(data['mapeo'].keys()), {slot['id'] for slot in plantilla.PLANTILLA_SLOTS})

    def test_sugerir_incluye_las_columnas_con_valores_en_blanco_recurrentes(self):
        # El fixture real (15 filas) tiene columnas con 3+ blancos de forma natural: "Alterno
        # Cliente" y "OBSERVACION" totalmente vacías (15), "Fecha compromiso pago" y
        # "Observaciones" con 14, "VENCE" con 3 — y "Causal" con solo 2, que NO debe aparecer.
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json')
        data = resp.json()
        self.assertIn('columnas_con_blancos', data)
        por_columna = {c['columna']: c for c in data['columnas_con_blancos']}
        self.assertEqual(por_columna['Alterno Cliente']['cantidad_en_blanco'], 15)
        self.assertEqual(por_columna['OBSERVACION']['cantidad_en_blanco'], 15)
        self.assertEqual(por_columna['VENCE']['cantidad_en_blanco'], 3)
        self.assertNotIn('Causal', por_columna)
        # Cada fila de ejemplo trae con qué ubicarla.
        ejemplo = por_columna['VENCE']['filas_ejemplo'][0]
        self.assertIn('numero_fila', ejemplo)
        self.assertIn('referencia', ejemplo)

    def test_previsualizar_recalcula_los_datos_sin_persistir(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/previsualizar', {
            'carga_id': carga_id, 'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Saldo'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('Suma de "Saldo"', data['datos']['kpi-1']['descripcion'])
        # No debe haber sobreescrito el layout (sigue con los datos ficticios de la siembra).
        kpi_1 = DashboardComponent.objects.get(layout__dashboard_id='finanzas', component_id='kpi-1')
        self.assertEqual(kpi_1.content, plantilla.datos_ficticios()['kpi-1'])

    def test_previsualizar_sin_mapeo_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/previsualizar', {'carga_id': carga_id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'MAPEO_REQUERIDO')

    def test_aplicar_sobreescribe_el_layout_y_marca_la_carga_procesada(self):
        carga_id = self._subir_archivo()
        sugerido = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json').json()

        resp = self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id, 'mapeo': sugerido['mapeo']}, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['components']), len(plantilla.PLANTILLA_SLOTS))

        carga = CargaArchivo.objects.get(id=carga_id)
        self.assertEqual(carga.estado, CargaArchivo.Estado.PROCESADO)

    def test_aplicar_respeta_el_chart_type_elegido_por_el_usuario(self):
        carga_id = self._subir_archivo()
        sugerido = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json').json()
        mapeo = sugerido['mapeo']
        mapeo['grafico-1']['chart_type'] = 'lineas'

        resp = self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id, 'mapeo': mapeo}, format='json')
        self.assertEqual(resp.status_code, 200)
        grafico_1 = next(c for c in resp.json()['components'] if c['component_id'] == 'grafico-1')
        self.assertEqual(grafico_1['chart_type'], 'lineas')

    def test_previsualizar_con_tipo_agregacion_conteo_unicos(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/previsualizar', {
            'carga_id': carga_id,
            'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Ruc Cliente', 'tipo_agregacion': 'conteo_unicos'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        datos = resp.json()['datos']['kpi-1']
        self.assertIn('Cantidad de valores únicos', datos['descripcion'])
        self.assertIsInstance(datos['valor'], int)

    def test_previsualizar_con_tipo_agregacion_promedio(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/previsualizar', {
            'carga_id': carga_id,
            'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Saldo', 'tipo_agregacion': 'promedio'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        datos = resp.json()['datos']['kpi-1']
        self.assertIn('Promedio de', datos['descripcion'])

    def test_previsualizar_con_filtro_de_columna_y_valor(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/previsualizar', {
            'carga_id': carga_id,
            'mapeo': {'kpi-1': {
                'disponible': True, 'columna_valor': 'Saldo',
                'columna_filtro': 'Causal', 'valor_filtro': 'GESTIONANDO',
            }},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('donde "Causal" = "GESTIONANDO"', resp.json()['datos']['kpi-1']['descripcion'])

    def test_valores_columna_devuelve_los_valores_distintos(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/valores-columna', {
            'carga_id': carga_id, 'columna': 'Causal',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('GESTIONANDO', data['valores'])
        self.assertEqual(data['valores'], sorted(data['valores']))

    def test_valores_columna_sin_columna_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/valores-columna', {'carga_id': carga_id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLUMNA_REQUERIDA')

    def test_valores_columna_inexistente_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/valores-columna', {
            'carga_id': carga_id, 'columna': 'no_existe',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'COLUMNA_INVALIDA')

    def test_valores_columna_respeta_el_alias_elegido(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/valores-columna', {
            'carga_id': carga_id, 'columna': 'Motivo', 'aliases': {'Causal': 'Motivo'},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('GESTIONANDO', resp.json()['valores'])

    def test_aplicar_sin_mapeo_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'MAPEO_REQUERIDO')

    def test_aplicar_guarda_una_copia_permanente_del_archivo(self):
        from django.conf import settings
        carga_id = self._subir_archivo()
        sugerido = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json').json()
        self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id, 'mapeo': sugerido['mapeo']}, format='json')

        carga = CargaArchivo.objects.get(id=carga_id)
        self.assertTrue(carga.archivo_permanente_nombre)
        ruta = settings.CARTERA_ARCHIVOS_DIR / carga.archivo_permanente_nombre
        self.assertTrue(ruta.exists())

    def test_el_mapeo_sigue_funcionando_aunque_el_archivo_temporal_ya_no_exista(self):
        # Simula lo que hace `clean_temp_uploads` a las 24h (borra el archivo temporal): en vez
        # de tocar el archivo físico (bloqueado por el propio proceso en Windows justo después de
        # leerlo con pandas), apunta `archivo_temp_nombre` a una ruta que no existe — si
        # `_leer_archivo_temporal_de_carga` intentara leer de ahí, fallaría.
        carga_id = self._subir_archivo()
        sugerido = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json').json()
        self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id, 'mapeo': sugerido['mapeo']}, format='json')

        carga = CargaArchivo.objects.get(id=carga_id)
        self.assertTrue(carga.archivo_permanente_nombre)
        carga.archivo_temp_nombre = 'no-existe.xlsx'
        carga.save(update_fields=['archivo_temp_nombre'])

        resp = self.client.post('/api/cartera/plantilla/previsualizar', {
            'carga_id': carga_id, 'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Saldo'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)


class ArchivoActualDashboardViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        usuario = User.objects.create_superuser(username='tester_archivo', email='ta2@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas')
        plantilla.sembrar_plantilla('finanzas')

    def _subir_archivo(self):
        with open(FIXTURE_PATH, 'rb') as f:
            resp = self.client.post('/api/cartera/validar-archivo', {'archivo': f, 'dashboard_id': 'finanzas'}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        return resp.json()['carga_id']

    def test_sin_archivo_aplicado_no_esta_disponible(self):
        resp = self.client.post('/api/cartera/plantilla/archivo-actual', {'dashboard_id': 'finanzas'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['disponible'])

    def test_tras_aplicar_un_mapeo_devuelve_el_archivo_y_sus_columnas(self):
        carga_id = self._subir_archivo()
        sugerido = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json').json()
        self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id, 'mapeo': sugerido['mapeo']}, format='json')

        resp = self.client.post('/api/cartera/plantilla/archivo-actual', {'dashboard_id': 'finanzas'}, format='json')

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['disponible'])
        self.assertEqual(data['carga_id'], carga_id)
        self.assertIn('Saldo', {c['nombre'] for c in data['columnas']})

    def test_sin_dashboard_id_devuelve_400(self):
        resp = self.client.post('/api/cartera/plantilla/archivo-actual', {}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'DASHBOARD_ID_REQUERIDO')

    def test_aplicar_dos_veces_no_duplica_componentes(self):
        carga_id = self._subir_archivo()
        sugerido = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json').json()
        self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id, 'mapeo': sugerido['mapeo']}, format='json')
        resp = self.client.post('/api/cartera/plantilla/aplicar', {'carga_id': carga_id, 'mapeo': sugerido['mapeo']}, format='json')
        self.assertEqual(len(resp.json()['components']), len(plantilla.PLANTILLA_SLOTS))


class AliasColumnasApiTests(TestCase):
    """El paso "renombrar columnas" (antes del mapeo): `aliases` ({nombre_original: nuevo_nombre})
    renombra el archivo antes de analizarlo, así que el resto del flujo (columnas devueltas,
    mapeo, datos calculados, títulos/descripciones) usa el nuevo nombre como si fuera el
    original."""

    def setUp(self):
        self.client = APIClient()
        usuario = User.objects.create_superuser(username='tester_alias', email='ta@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas')
        plantilla.sembrar_plantilla('finanzas')

    def _subir_archivo(self):
        with open(FIXTURE_PATH, 'rb') as f:
            resp = self.client.post('/api/cartera/validar-archivo', {'archivo': f, 'dashboard_id': 'finanzas'}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        return resp.json()['carga_id']

    def test_sugerir_aplica_el_alias_a_las_columnas_devueltas(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {
            'carga_id': carga_id, 'aliases': {'Saldo': 'Monto Adeudado'},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        nombres = {c['nombre'] for c in resp.json()['columnas']}
        self.assertIn('Monto Adeudado', nombres)
        self.assertNotIn('Saldo', nombres)

    def test_previsualizar_calcula_contra_el_nombre_renombrado(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/previsualizar', {
            'carga_id': carga_id,
            'aliases': {'Saldo': 'Monto Adeudado'},
            'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Monto Adeudado'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Monto Adeudado', resp.json()['datos']['kpi-1']['descripcion'])

    def test_aplicar_persiste_el_componente_con_el_nombre_renombrado(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/aplicar', {
            'carga_id': carga_id,
            'aliases': {'Saldo': 'Monto Adeudado'},
            'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Monto Adeudado'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        kpi_1 = DashboardComponent.objects.get(layout__dashboard_id='finanzas', component_id='kpi-1')
        self.assertIn('Monto Adeudado', kpi_1.content['descripcion'])

    def test_un_alias_repetido_en_dos_columnas_devuelve_400(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {
            'carga_id': carga_id, 'aliases': {'Saldo': 'Mismo Nombre', 'Telefono': 'Mismo Nombre'},
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'ALIAS_DUPLICADO')

    def test_sin_aliases_se_comporta_igual_que_antes(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Saldo', {c['nombre'] for c in resp.json()['columnas']})


class ValoresBlancosApiTests(TestCase):
    """El paso "valores en blanco" (entre renombrar y mapeo, para columnas con más de 10 blancos):
    `valores_blancos` ({columna: valor_de_reemplazo}) completa esas celdas antes de analizar,
    igual que `aliases` renombra columnas — afecta de verdad los cálculos, no es una etiqueta de
    vista. "Alterno Cliente" del fixture tiene sus 15 filas en blanco (columna totalmente vacía),
    ideal para probar el reemplazo sin ambigüedad."""

    def setUp(self):
        self.client = APIClient()
        usuario = User.objects.create_superuser(username='tester_blancos', email='tb@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas')
        plantilla.sembrar_plantilla('finanzas')

    def _subir_archivo(self):
        with open(FIXTURE_PATH, 'rb') as f:
            resp = self.client.post('/api/cartera/validar-archivo', {'archivo': f, 'dashboard_id': 'finanzas'}, format='multipart')
        self.assertEqual(resp.status_code, 200)
        return resp.json()['carga_id']

    def test_sugerir_con_valores_blancos_completa_la_columna(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {
            'carga_id': carga_id, 'valores_blancos': {'Alterno Cliente': '5'},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        columna = next(c for c in resp.json()['columnas'] if c['nombre'] == 'Alterno Cliente')
        self.assertEqual(columna['valores_no_nulos'], 15)
        self.assertTrue(columna['apta_para_valor'])

    def test_columna_sin_valor_elegido_no_se_toca(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {
            'carga_id': carga_id, 'valores_blancos': {'OBSERVACION': '5'},
        }, format='json')
        columna = next(c for c in resp.json()['columnas'] if c['nombre'] == 'Alterno Cliente')
        self.assertEqual(columna['valores_no_nulos'], 0)

    def test_un_valor_en_blanco_vacio_no_reemplaza(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/sugerir', {
            'carga_id': carga_id, 'valores_blancos': {'Alterno Cliente': '   '},
        }, format='json')
        columna = next(c for c in resp.json()['columnas'] if c['nombre'] == 'Alterno Cliente')
        self.assertEqual(columna['valores_no_nulos'], 0)

    def test_previsualizar_incluye_el_reemplazo_en_la_suma(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/previsualizar', {
            'carga_id': carga_id,
            'valores_blancos': {'Alterno Cliente': '100'},
            'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Alterno Cliente'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['datos']['kpi-1']['valor'], 1500)  # 15 filas x 100

    def test_aplicar_persiste_el_reemplazo_en_el_kpi_el_archivo_permanente_y_el_historico(self):
        carga_id = self._subir_archivo()
        resp = self.client.post('/api/cartera/plantilla/aplicar', {
            'carga_id': carga_id,
            'valores_blancos': {'Alterno Cliente': '7'},
            'columnas_historicas': ['Alterno Cliente'],
            'mapeo': {'kpi-1': {'disponible': True, 'columna_valor': 'Alterno Cliente'}},
        }, format='json')
        self.assertEqual(resp.status_code, 200)

        kpi_1 = DashboardComponent.objects.get(layout__dashboard_id='finanzas', component_id='kpi-1')
        self.assertEqual(kpi_1.content['valor'], 105)  # 15 filas x 7

        carga = CargaArchivo.objects.get(id=carga_id)
        filas = FilaArchivoHistorico.objects.filter(carga=carga)
        self.assertEqual(filas.count(), 15)
        self.assertTrue(all(f.datos.get('Alterno Cliente') == '7' for f in filas))

        # El reemplazo queda fijado en el archivo permanente: una consulta posterior sin volver a
        # mandar `valores_blancos` ya lo ve completo.
        resp2 = self.client.post('/api/cartera/plantilla/sugerir', {'carga_id': carga_id}, format='json')
        columna2 = next(c for c in resp2.json()['columnas'] if c['nombre'] == 'Alterno Cliente')
        self.assertEqual(columna2['valores_no_nulos'], 15)
