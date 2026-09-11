import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from cartera.exceptions import CarteraError
from cartera.models import Dashboard
from cartera.services import dashboard_interpretation as di
from cartera.services import dashboard_layout as dl

User = get_user_model()


def _cliente_autenticado():
    client = APIClient()
    usuario = User.objects.create_superuser(
        username=f'tester_{User.objects.count()}', email=f'tester{User.objects.count()}@example.com',
        password='Clave-Segura-123',
    )
    client.force_authenticate(user=usuario)
    return client


def _cliente_con_permisos(*codenames):
    """A diferencia de `_cliente_autenticado` (superusuario, tiene todo el catálogo), arma un
    usuario normal con exactamente los codenames indicados — para probar que `dashboard.interpretar`/
    `dashboard.hallazgos_ia` son permisos propios, no un alias de `dashboard.view`."""
    from django.contrib.auth.models import Permission

    client = APIClient()
    usuario = User.objects.create_user(
        username=f'user_{User.objects.count()}', email=f'user{User.objects.count()}@example.com',
        password='Clave-Segura-123',
    )
    for codename in codenames:
        usuario.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label='permissions'))
    client.force_authenticate(user=usuario)
    return client


def _respuesta_gemini(texto):
    respuesta = mock.Mock(status_code=200)
    respuesta.json.return_value = {'candidates': [{'content': {'parts': [{'text': texto}]}}]}
    return respuesta


class GenerarInterpretacionServiceTests(TestCase):
    def setUp(self):
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas', area='Finanzas y Contabilidad')

    @override_settings(GEMINI_API_KEY='')
    def test_sin_api_key_configurada_lanza_error_de_negocio(self):
        with self.assertRaises(CarteraError) as ctx:
            di.generar_interpretacion('finanzas')
        self.assertEqual(ctx.exception.codigo, 'IA_NO_CONFIGURADA')

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    def test_dashboard_sin_componentes_visibles_lanza_error_de_negocio(self):
        with self.assertRaises(CarteraError) as ctx:
            di.generar_interpretacion('finanzas')
        self.assertEqual(ctx.exception.codigo, 'SIN_DATOS')

    @override_settings(GEMINI_API_KEY='')
    def test_dashboard_inexistente_lanza_error_de_negocio(self):
        with self.assertRaises(CarteraError) as ctx:
            di.generar_interpretacion('no-existe')
        # Sin API key configurada, esa validación corre primero — se cubre el caso "no existe"
        # por separado más abajo, con la key sí configurada.
        self.assertEqual(ctx.exception.codigo, 'IA_NO_CONFIGURADA')

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    def test_dashboard_inexistente_con_api_key_configurada_lanza_error_de_negocio(self):
        with self.assertRaises(CarteraError) as ctx:
            di.generar_interpretacion('no-existe')
        self.assertEqual(ctx.exception.codigo, 'DASHBOARD_NO_ENCONTRADO')

    @override_settings(GEMINI_API_KEY='clave-de-prueba', GEMINI_MODEL='gemini-2.5-flash')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_llamada_exitosa_devuelve_el_texto_generado(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total cartera', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1000.0},
        })
        post_mock.return_value = _respuesta_gemini('El dashboard muestra una cartera total de 1000.')

        texto = di.generar_interpretacion('finanzas')

        self.assertEqual(texto, 'El dashboard muestra una cartera total de 1000.')
        url_llamada, kwargs = post_mock.call_args
        self.assertIn('gemini-2.5-flash', url_llamada[0])
        # La credencial va en el encabezado, nunca en la cadena de consulta (donde la capturaba
        # cualquier log de URLs). Se verifica también que no quede un `params` con la clave.
        self.assertEqual(kwargs['headers'], {'x-goog-api-key': 'clave-de-prueba'})
        self.assertNotIn('params', kwargs)
        self.assertIn('Total cartera', kwargs['json']['contents'][0]['parts'][0]['text'])

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_componentes_ocultos_no_se_incluyen_en_el_prompt(self, post_mock):
        layout = dl.agregar_componente_generado('finanzas', {
            'titulo': 'Oculto', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        componente = layout.components.get()
        componente.is_visible = False
        componente.save(update_fields=['is_visible'])
        post_mock.return_value = _respuesta_gemini('texto')

        with self.assertRaises(CarteraError) as ctx:
            di.generar_interpretacion('finanzas')
        self.assertEqual(ctx.exception.codigo, 'SIN_DATOS')
        post_mock.assert_not_called()

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_incluye_el_contexto_del_dashboard_en_el_prompt_si_esta_cargado(self, post_mock):
        Dashboard.objects.filter(dashboard_id='finanzas').update(contexto='Datos de cartera vencida de la región norte.')
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini('texto')

        di.generar_interpretacion('finanzas')

        prompt = post_mock.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        self.assertIn('Datos de cartera vencida de la región norte.', prompt)

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_sin_contexto_cargado_no_agrega_la_seccion_de_contexto(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini('texto')

        di.generar_interpretacion('finanzas')

        prompt = post_mock.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        # La instrucción genérica de "Instrucción del usuario para este componente" siempre
        # menciona la frase "Contexto adicional" (para cuando SÍ haya una) — lo que este test
        # verifica es que no se agregue el bloque del contexto del DASHBOARD (`_bloque_contexto`).
        self.assertNotIn('Contexto adicional sobre este dashboard', prompt)

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_incluye_la_instruccion_ia_de_un_componente_de_zona_personal_en_el_prompt(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Saldo por gestor', 'columna_valor': 'saldo', 'columna_categoria': 'gestor',
            'datos': {'tipo': 'chart', 'titulo': 'Saldo por gestor', 'categorias': ['Ana'], 'valores': [100.0]},
            'zona': 'personal', 'instruccion_ia': 'Explicá los totales por la causal de gestión.',
            'columna_contexto_ia': 'causal',
            'contexto_ia_datos': {'categorias': ['Pago parcial', 'Sin contacto'], 'valores': [60.0, 40.0]},
        })
        post_mock.return_value = _respuesta_gemini('texto')

        di.generar_interpretacion('finanzas')

        prompt = post_mock.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        self.assertIn('Instrucción del usuario para este componente: "Explicá los totales por la causal de gestión."', prompt)
        self.assertIn('Contexto adicional (desglose por "causal")', prompt)
        self.assertIn('Pago parcial: 60.00', prompt)

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_sin_instruccion_ia_no_agrega_nada_para_ese_componente(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini('texto')

        di.generar_interpretacion('finanzas')

        prompt = post_mock.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        # La instrucción genérica siempre menciona la frase (para cuando SÍ haya una) — lo que
        # este test verifica es que no se agregue el bloque CON CONTENIDO real de este componente.
        self.assertNotIn('Instrucción del usuario para este componente: "', prompt)

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_error_http_del_proveedor_se_traduce_a_error_de_negocio(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        # `text` explícito: el servicio ahora registra el cuerpo del error en el log del servidor
        # para poder diagnosticarlo (antes se descartaba), así que el doble tiene que parecerse a
        # una `requests.Response` de verdad, donde `text` siempre es un str.
        post_mock.return_value = mock.Mock(status_code=500, text='quota exceeded')

        with self.assertRaises(CarteraError) as ctx:
            di.generar_interpretacion('finanzas')
        self.assertEqual(ctx.exception.codigo, 'IA_ERROR')


class DashboardInterpretacionViewTests(TestCase):
    def setUp(self):
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas', area='Finanzas y Contabilidad')
        self.client = _cliente_autenticado()

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_post_devuelve_la_interpretacion_generada(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total cartera', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1000.0},
        })
        post_mock.return_value = _respuesta_gemini('Interpretación de prueba.')

        resp = self.client.post('/api/dashboards/finanzas/interpretacion')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'interpretacion': 'Interpretación de prueba.'})

    @override_settings(GEMINI_API_KEY='')
    def test_post_sin_api_key_configurada_responde_400_con_codigo_de_error(self):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total cartera', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1000.0},
        })

        resp = self.client.post('/api/dashboards/finanzas/interpretacion')

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['error'], 'IA_NO_CONFIGURADA')

    def test_post_sin_sesion_responde_401(self):
        client = APIClient()
        resp = client.post('/api/dashboards/finanzas/interpretacion')
        self.assertEqual(resp.status_code, 401)

    def test_post_con_dashboard_view_pero_sin_dashboard_interpretar_responde_403(self):
        # Ver el dashboard no alcanza — dashboard.interpretar es un permiso propio, separado a
        # propósito para poder controlar el uso de IA sin depender de quién puede ver el dashboard.
        cliente = _cliente_con_permisos('dashboard.view')
        resp = cliente.post('/api/dashboards/finanzas/interpretacion')
        self.assertEqual(resp.status_code, 403)

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_post_con_dashboard_view_y_dashboard_interpretar_funciona(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini('Interpretación de prueba.')
        cliente = _cliente_con_permisos('dashboard.view', 'dashboard.interpretar')

        resp = cliente.post('/api/dashboards/finanzas/interpretacion')

        self.assertEqual(resp.status_code, 200)


def _respuesta_gemini_json(hallazgos):
    respuesta = mock.Mock(status_code=200)
    respuesta.json.return_value = {'candidates': [{'content': {'parts': [{'text': json.dumps(hallazgos)}]}}]}
    return respuesta


class GenerarHallazgosIAServiceTests(TestCase):
    def setUp(self):
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas', area='Finanzas y Contabilidad')
        # `generar_hallazgos_ia` cachea por hash del prompt para no repetir la llamada externa en
        # cada apertura del dashboard. La caché por defecto es en memoria del proceso, así que sin
        # limpiarla dos tests que armen el mismo prompt se contaminan entre sí.
        cache.clear()
        self.addCleanup(cache.clear)

    @override_settings(GEMINI_API_KEY='')
    def test_sin_api_key_configurada_lanza_error_de_negocio(self):
        with self.assertRaises(CarteraError) as ctx:
            di.generar_hallazgos_ia('finanzas')
        self.assertEqual(ctx.exception.codigo, 'IA_NO_CONFIGURADA')

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    def test_dashboard_sin_componentes_visibles_lanza_error_de_negocio(self):
        with self.assertRaises(CarteraError) as ctx:
            di.generar_hallazgos_ia('finanzas')
        self.assertEqual(ctx.exception.codigo, 'SIN_DATOS')

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_llamada_exitosa_devuelve_un_hallazgo_por_componente(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total cartera', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1000.0},
        })
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Por ciudad', 'columna_valor': 'saldo', 'columna_categoria': 'ciudad',
            'datos': {'tipo': 'chart', 'categorias': ['Quito'], 'valores': [100.0]},
        })
        post_mock.return_value = _respuesta_gemini_json({
            'total-cartera': 'El valor asciende a **1000**.',
            'por-ciudad': '**Quito** concentra el total.',
        })

        hallazgos = di.generar_hallazgos_ia('finanzas')

        self.assertEqual(hallazgos, {
            'total-cartera': 'El valor asciende a **1000**.',
            'por-ciudad': '**Quito** concentra el total.',
        })
        kwargs = post_mock.call_args.kwargs
        self.assertEqual(kwargs['json']['generationConfig'], {'responseMimeType': 'application/json'})
        self.assertIn('total-cartera', kwargs['json']['contents'][0]['parts'][0]['text'])

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_incluye_el_contexto_del_dashboard_en_el_prompt_si_esta_cargado(self, post_mock):
        Dashboard.objects.filter(dashboard_id='finanzas').update(contexto='Ventas del canal digital.')
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini_json({'total': 'texto'})

        di.generar_hallazgos_ia('finanzas')

        prompt = post_mock.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        self.assertIn('Ventas del canal digital.', prompt)

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_ignora_ids_que_no_corresponden_a_ningun_componente_visible(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini_json({
            'total': 'texto válido', 'id-inventado': 'no debería aparecer',
        })

        hallazgos = di.generar_hallazgos_ia('finanzas')

        self.assertEqual(hallazgos, {'total': 'texto válido'})

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_respuesta_no_es_json_valido_se_traduce_a_error_de_negocio(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini('esto no es JSON')

        with self.assertRaises(CarteraError) as ctx:
            di.generar_hallazgos_ia('finanzas')
        self.assertEqual(ctx.exception.codigo, 'IA_ERROR')


class DashboardHallazgosIAViewTests(TestCase):
    def setUp(self):
        Dashboard.objects.create(dashboard_id='finanzas', name='Finanzas', area='Finanzas y Contabilidad')
        self.client = _cliente_autenticado()

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_post_devuelve_los_hallazgos_generados(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini_json({'total': 'Hallazgo de prueba.'})

        resp = self.client.post('/api/dashboards/finanzas/hallazgos-ia')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'hallazgos': {'total': 'Hallazgo de prueba.'}})

    def test_post_sin_sesion_responde_401(self):
        client = APIClient()
        resp = client.post('/api/dashboards/finanzas/hallazgos-ia')
        self.assertEqual(resp.status_code, 401)

    def test_post_con_dashboard_view_pero_sin_dashboard_hallazgos_ia_responde_403(self):
        cliente = _cliente_con_permisos('dashboard.view')
        resp = cliente.post('/api/dashboards/finanzas/hallazgos-ia')
        self.assertEqual(resp.status_code, 403)

    @override_settings(GEMINI_API_KEY='clave-de-prueba')
    @mock.patch('cartera.services.dashboard_interpretation.requests.post')
    def test_post_con_dashboard_view_y_dashboard_hallazgos_ia_funciona(self, post_mock):
        dl.agregar_componente_generado('finanzas', {
            'titulo': 'Total', 'columna_valor': 'saldo', 'columna_categoria': None,
            'datos': {'tipo': 'kpi', 'valor': 1.0},
        })
        post_mock.return_value = _respuesta_gemini_json({'total': 'Hallazgo de prueba.'})
        cliente = _cliente_con_permisos('dashboard.view', 'dashboard.hallazgos_ia')

        resp = cliente.post('/api/dashboards/finanzas/hallazgos-ia')

        self.assertEqual(resp.status_code, 200)
