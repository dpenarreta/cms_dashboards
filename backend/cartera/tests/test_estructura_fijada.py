"""La estructura de un dashboard bloqueado sobrevive a cualquier reescritura del layout.

El bloqueo de `services/desbloqueo.py` cubre los caminos que pasan por el editor. Esto cubre el
resto: operaciones de DATOS —borrar todo, recargar el archivo, restablecer el diseño— que
reescriben el layout como efecto secundario y se llevaban la estructura puesta.

El caso que lo motivó es real y está reproducido acá: el Dashboard Directorio de producción
amaneció convertido en el genérico después de un "Borrar datos" seguido de una reconexión de la
fuente. Las nueve secciones del informe habían desaparecido.

Lo que se conserva son tipos, orden, dimensiones y visibilidad. El contenido no: los datos son
justamente lo que esas operaciones vienen a cambiar.
"""

import pandas as pd
from django.test import TestCase

from cartera.models import Dashboard, DashboardComponent
from cartera.services import dashboard_layout as dl
from cartera.services import estructura, plantilla
from cartera.services.dashboards import borrar_datos_dashboard, crear_dashboard

DASHBOARD = 'finanzas'


def _df():
    return pd.DataFrame({'Saldo': [100.0, 200.0], 'Zona': ['Norte', 'Sur']})


def _con_secciones(cantidad=3):
    """Las 13 posiciones de plantilla MÁS secciones propias, como el Dashboard Directorio.

    No se reemplazan las existentes a propósito: el caso real tiene las dos cosas, y es lo que
    hace que aplicar un mapeo (que reconstruye esas 13) sea un escenario interesante.
    """
    for i in range(1, cantidad + 1):
        dl.agregar_componente_generado(DASHBOARD, {
            # Con `calculo` explícito, como los crea la Zona Personal: es lo que hace que el
            # componente guarde su `mapeo`, y sin mapeo no habría nada que conservar al reponer.
            'titulo': f'Sección {i}', 'calculo': 'chart',
            'columna_valor': 'Saldo', 'columna_categoria': 'Zona',
            'datos': {'tipo': 'chart', 'categorias': ['A'], 'valores': [1.0]},
            'zona': 'personal', 'ancho_columnas': 2,
        }, reemplazar_existentes=False)
    return dl.obtener_o_crear_layout(DASHBOARD)


def _bloquear_y_fijar():
    Dashboard.objects.filter(dashboard_id=DASHBOARD).update(estructura_bloqueada=True)
    return estructura.fijar(DASHBOARD)


def _estructura_actual():
    return [
        (c.component_id, c.type, c.order, c.width, c.height, c.is_visible)
        for c in DashboardComponent.objects.filter(layout__dashboard_id=DASHBOARD).order_by('order')
    ]


class EstructuraQueSobreviveTests(TestCase):
    def setUp(self):
        crear_dashboard(nombre='Finanzas')
        _con_secciones()
        self.esperada = None
        _bloquear_y_fijar()
        self.esperada = _estructura_actual()

    def test_borrar_todos_los_datos_no_se_lleva_la_estructura(self):
        # El escenario exacto de producción: "Borrar datos" elimina los componentes propios y
        # resiembra las 13 posiciones de ejemplo.
        borrar_datos_dashboard(DASHBOARD, confirmacion_nombre='Finanzas')
        self.assertEqual(_estructura_actual(), self.esperada)

    def test_despues_de_borrar_las_secciones_conservan_su_mapeo_para_recalcularse(self):
        # Reponer un componente sin su mapeo lo dejaría ahí pero vacío para siempre: ni
        # `reprocesar_dashboards` podría llenarlo.
        antes = DashboardComponent.objects.get(
            layout__dashboard_id=DASHBOARD, component_id='seccion-1',
        ).mapeo
        self.assertTrue(antes, 'la sección de prueba tiene que nacer con mapeo')

        borrar_datos_dashboard(DASHBOARD, confirmacion_nombre='Finanzas')

        repuesto = DashboardComponent.objects.get(
            layout__dashboard_id=DASHBOARD, component_id='seccion-1',
        )
        self.assertEqual(repuesto.mapeo, antes)

    def test_aplicar_un_mapeo_nuevo_no_reordena_ni_redimensiona(self):
        # Cargar un archivo nuevo o conectar la fuente reconstruye las 13 posiciones y empuja el
        # resto detrás. La estructura tiene que quedar como estaba.
        plantilla.aplicar_mapeo(DASHBOARD, _df(), {'kpi-1': {'disponible': True, 'columna_valor': 'Saldo'}})
        self.assertEqual(_estructura_actual(), self.esperada)

    def test_restablecer_el_diseno_no_muestra_lo_que_estaba_oculto(self):
        dl.restablecer_layout(DASHBOARD, 'test')
        self.assertEqual(_estructura_actual(), self.esperada)

    def test_no_se_cuela_un_componente_que_no_estaba_en_la_foto(self):
        # Si la reposición dejara pasar componentes nuevos, sería la puerta de atrás del bloqueo.
        dl.agregar_componente_presentacional(DASHBOARD, 'title', zona='personal')
        self.assertEqual(_estructura_actual(), self.esperada)

    def test_los_datos_si_se_pueden_seguir_actualizando(self):
        # La estructura se repone, el contenido no: bloquear el contenido dejaría al dashboard
        # sin poder actualizarse, que es lo contrario de lo que se busca.
        plantilla.aplicar_mapeo(DASHBOARD, _df(), {'kpi-1': {'disponible': True, 'columna_valor': 'Saldo'}})
        kpi = DashboardComponent.objects.get(layout__dashboard_id=DASHBOARD, component_id='kpi-1')
        self.assertEqual(kpi.content.get('valor'), 300.0)


class SinBloqueoNoSeReponeNadaTests(TestCase):
    """El comportamiento de todos los demás dashboards no cambia."""

    def setUp(self):
        crear_dashboard(nombre='Finanzas')
        _con_secciones()

    def test_un_dashboard_sin_bloquear_se_puede_vaciar_como_siempre(self):
        borrar_datos_dashboard(DASHBOARD, confirmacion_nombre='Finanzas')
        ids = {c.component_id for c in DashboardComponent.objects.filter(layout__dashboard_id=DASHBOARD)}
        self.assertNotIn('seccion-1', ids)

    def test_desbloquear_deja_de_reponer(self):
        _bloquear_y_fijar()
        Dashboard.objects.filter(dashboard_id=DASHBOARD).update(estructura_bloqueada=False)
        estructura.limpiar(DASHBOARD)

        borrar_datos_dashboard(DASHBOARD, confirmacion_nombre='Finanzas')
        ids = {c.component_id for c in DashboardComponent.objects.filter(layout__dashboard_id=DASHBOARD)}
        self.assertNotIn('seccion-1', ids)


class FotoDeLaEstructuraTests(TestCase):
    def setUp(self):
        crear_dashboard(nombre='Finanzas')
        _con_secciones(2)

    def test_sin_bloqueo_la_foto_no_se_usa_aunque_exista(self):
        # `fijar` se puede llamar sobre un dashboard libre; lo que decide es el bloqueo.
        estructura.fijar(DASHBOARD)
        self.assertEqual(estructura.fijada_de(DASHBOARD), [])

    def test_la_foto_guarda_lo_estructural_de_cada_componente(self):
        _bloquear_y_fijar()
        foto = estructura.fijada_de(DASHBOARD)
        self.assertEqual(len(foto), DashboardComponent.objects.filter(layout__dashboard_id=DASHBOARD).count())
        for campo in estructura.CAMPOS_ESTRUCTURALES:
            with self.subTest(campo=campo):
                self.assertIn(campo, foto[0])

    def test_volver_a_fijar_reemplaza_la_foto(self):
        # Es lo que hace la siembra: después de ella, la estructura válida es la nueva.
        _bloquear_y_fijar()
        cuantos_antes = len(estructura.fijada_de(DASHBOARD))
        Dashboard.objects.filter(dashboard_id=DASHBOARD).update(estructura_bloqueada=False)
        _con_secciones(5)
        Dashboard.objects.filter(dashboard_id=DASHBOARD).update(estructura_bloqueada=True)
        estructura.fijar(DASHBOARD)

        self.assertNotEqual(len(estructura.fijada_de(DASHBOARD)), cuantos_antes)
