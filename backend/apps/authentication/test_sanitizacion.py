"""Saneo del HTML de las plantillas de correo.

Dos mitades igual de importantes: que lo peligroso no sobreviva, y que lo legítimo sí. La segunda
no es un detalle de comodidad — un saneo que rompe el diseño de los correos se termina desactivando,
y entonces no protege de nada. Por eso la plantilla real del proyecto es un caso de prueba.
"""

from django.test import TestCase
from rest_framework import serializers

from .email_template_defaults import DEFAULT_EMAIL_TEMPLATES
from .sanitizacion import sanear_html_de_correo
from .serializers import EmailTemplateUpdateSerializer

PLANTILLA_REAL = DEFAULT_EMAIL_TEMPLATES['password_reset']['html_body']


class LoPeligrosoNoSobreviveTests(TestCase):
    def test_neutraliza_los_vectores_conocidos(self):
        casos = [
            ('<script>alert(1)</script>', 'script'),
            ('<p>hola</p><img src=x onerror="alert(1)">', 'onerror'),
            ('<a href="javascript:alert(1)">clic</a>', 'javascript:'),
            ('<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>', 'data:'),
            ('<iframe src="https://malo"></iframe>', 'iframe'),
            ('<object data="x"></object>', 'object'),
            ('<embed src="x">', 'embed'),
            ('<form action="https://malo"><input name="p"></form>', 'form'),
            ('<p onclick="alert(1)">texto</p>', 'onclick'),
            ('<div onmouseover="alert(1)">texto</div>', 'onmouseover'),
            ('<svg><script>alert(1)</script></svg>', 'svg'),
            ('<meta http-equiv="refresh" content="0;url=https://malo">', 'http-equiv'),
            ('<base href="https://malo/">', '<base'),
            ('<style>body{background:url(javascript:alert(1))}</style>', '<style'),
        ]
        for entrada, prohibido in casos:
            with self.subTest(prohibido=prohibido):
                self.assertNotIn(prohibido, sanear_html_de_correo(entrada))

    def test_un_body_con_onload_pierde_el_manejador_pero_conserva_el_contenido(self):
        # El `<body>` se reconstruye desde un esqueleto fijo, así que sus atributos no llegan salvo
        # `style`: es justamente lo que elimina de raíz `onload` y compañía.
        salida = sanear_html_de_correo('<html><body onload="alert(1)"><p>hola</p></body></html>')
        self.assertNotIn('onload', salida)
        self.assertIn('<p>hola</p>', salida)

    def test_el_estilo_del_body_no_puede_colar_atributos(self):
        salida = sanear_html_de_correo('<html><body style="color: red" onload="alert(1)"><p>x</p></body></html>')
        self.assertIn('color: red', salida)
        self.assertNotIn('onload', salida)


class LoLegitimoSobreviveTests(TestCase):
    """Si estas pruebas fallan, el saneo está rompiendo correos reales."""

    def setUp(self):
        self.limpio = sanear_html_de_correo(PLANTILLA_REAL)

    def test_conserva_la_estructura_de_documento(self):
        for marca in ('<!DOCTYPE html>', '<html lang="es">', '<meta charset="utf-8">', '<body'):
            with self.subTest(marca=marca):
                self.assertIn(marca, self.limpio)

    def test_conserva_el_estilo_del_body(self):
        # Es el fondo y el padding del correo entero: los saneadores de fragmentos se lo comen, y
        # esa es exactamente la razón por la que este módulo reconstruye el documento.
        self.assertIn('background: #eeeeee', self.limpio)
        self.assertIn('padding: 24px', self.limpio)

    def test_conserva_los_estilos_en_linea_del_contenido(self):
        # Un correo se maqueta con estilos en línea porque los clientes ignoran las hojas de estilo.
        self.assertIn('style="max-width: 480px', self.limpio)
        self.assertIn('text-align: center', self.limpio)

    def test_conserva_las_variables_de_plantilla(self):
        for variable in ('{{ site_name }}', '{{ nombre_usuario }}', '{{ enlace }}',
                         '{{ minutos_expiracion }}', '{{ color_primary }}'):
            with self.subTest(variable=variable):
                self.assertIn(variable, self.limpio)

    def test_conserva_el_enlace_con_su_variable_como_href(self):
        self.assertIn('href="{{ enlace }}"', self.limpio)

    def test_es_idempotente(self):
        self.assertEqual(sanear_html_de_correo(self.limpio), self.limpio)

    def test_conserva_lo_que_produce_el_editor(self):
        # Encabezados, negrita/cursiva/subrayado, color, alineación, listas y enlaces: todo lo que
        # ofrece la barra de herramientas de `EmailTemplatesPage`.
        editor = (
            '<h1>Título</h1><p><strong>negrita</strong> <em>cursiva</em> <u>subrayado</u></p>'
            '<p><span style="color: rgb(230, 0, 0);">color</span></p>'
            '<p class="ql-align-center">centrado</p>'
            '<ol><li data-list="bullet">uno</li><li data-list="ordered">dos</li></ol>'
            '<p><a href="https://ejemplo.com" target="_blank">enlace</a></p>'
        )
        salida = sanear_html_de_correo(editor)
        for marca in ('<h1>', '<strong>', '<em>', '<u>', 'color: rgb(230, 0, 0)',
                      'class="ql-align-center"', 'data-list="bullet"', 'href="https://ejemplo.com"',
                      'target="_blank"'):
            with self.subTest(marca=marca):
                self.assertIn(marca, salida)

    def test_conserva_una_maquetacion_con_tablas(self):
        # Lo que produce cualquier herramienta de correo al exportar HTML.
        entrada = ('<table width="600" cellpadding="0" bgcolor="#ffffff"><tr><td align="center" '
                   'style="padding: 10px">celda</td></tr></table>')
        salida = sanear_html_de_correo(entrada)
        for marca in ('<table', 'width="600"', 'bgcolor="#ffffff"', 'align="center"', 'padding: 10px'):
            with self.subTest(marca=marca):
                self.assertIn(marca, salida)


class FragmentosYBordesTests(TestCase):
    def test_un_fragmento_sin_body_vuelve_como_fragmento(self):
        salida = sanear_html_de_correo('<p>solo un párrafo</p>')
        self.assertEqual(salida, '<p>solo un párrafo</p>')
        self.assertNotIn('<!DOCTYPE', salida)

    def test_una_cadena_vacia_se_devuelve_igual(self):
        self.assertEqual(sanear_html_de_correo(''), '')
        self.assertEqual(sanear_html_de_correo('   '), '   ')

    def test_un_documento_sin_cerrar_el_body_se_sanea_igual(self):
        salida = sanear_html_de_correo('<html><body><p>hola</p><script>alert(1)</script>')
        self.assertNotIn('script', salida)
        self.assertIn('hola', salida)


class SerializerTests(TestCase):
    """El saneo tiene que estar en el camino de guardado, no solo disponible como función."""

    def test_guardar_sanea_el_html(self):
        serializer = EmailTemplateUpdateSerializer(
            data={'subject': 'Asunto', 'html_body': '<p>ok</p><script>alert(1)</script>'},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['html_body'], '<p>ok</p>')

    def test_guardar_no_rechaza_el_contenido_peligroso_sino_que_lo_limpia(self):
        # Devolver un 400 obligaría a quien edita a adivinar qué parte de su HTML ofende; y el
        # editor no ofrece forma de escribir un `<script>`, así que no es un error del usuario.
        serializer = EmailTemplateUpdateSerializer(
            data={'subject': 'Asunto', 'html_body': '<script>alert(1)</script>'},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_guardar_conserva_la_plantilla_real_sin_cambios_de_fondo(self):
        serializer = EmailTemplateUpdateSerializer(data={'subject': 'Asunto', 'html_body': PLANTILLA_REAL})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        guardado = serializer.validated_data['html_body']
        self.assertIn('background: #eeeeee', guardado)
        self.assertIn('href="{{ enlace }}"', guardado)

    def test_el_asunto_no_admite_html_ejecutable_via_html_body(self):
        with self.assertRaises(serializers.ValidationError):
            EmailTemplateUpdateSerializer(data={'subject': 'x' * 201, 'html_body': '<p>x</p>'}).is_valid(
                raise_exception=True,
            )
