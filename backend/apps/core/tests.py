import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import BmpImagePlugin, Image
from rest_framework import serializers

from .audit import mask_sensitive_fields
from .imagenes import BYTES_DE_CABECERA, CampoImagenSegura, validar_extension_y_firma


class MaskSensitiveFieldsTests(TestCase):
    def test_enmascara_claves_sensibles_sin_tocar_el_resto(self):
        resultado = mask_sensitive_fields({'username': 'ana', 'password': 'secreta123', 'refresh_token': 'abc.def.ghi'})
        self.assertEqual(resultado['username'], 'ana')
        self.assertEqual(resultado['password'], '***')
        self.assertEqual(resultado['refresh_token'], '***')

    def test_valores_no_diccionario_se_devuelven_igual(self):
        self.assertEqual(mask_sensitive_fields(None), None)
        self.assertEqual(mask_sensitive_fields('texto'), 'texto')


def _imagen(formato, nombre):
    """Imagen real del formato pedido, guardada con el nombre (y extensión) que se indique."""
    buffer = io.BytesIO()
    Image.new('RGB', (8, 8), (255, 0, 0)).save(buffer, format=formato)
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type='image/png')


class ValidarExtensionYFirmaTests(TestCase):
    def test_acepta_los_tres_formatos_permitidos(self):
        for formato, nombre in (('PNG', 'a.png'), ('JPEG', 'a.jpg'), ('JPEG', 'a.jpeg'), ('WEBP', 'a.webp')):
            with self.subTest(formato=formato, nombre=nombre):
                cabecera = _imagen(formato, nombre).read(BYTES_DE_CABECERA)
                self.assertEqual(validar_extension_y_firma(nombre, cabecera), formato)

    def test_rechaza_un_formato_de_imagen_fuera_de_la_lista(self):
        # BMP es una imagen válida para Pillow, pero no está permitida: el punto es que la lista
        # sea cerrada, no que se distinga "imagen" de "no imagen".
        cabecera = _imagen('BMP', 'a.bmp').read(BYTES_DE_CABECERA)
        with self.assertRaises(serializers.ValidationError):
            validar_extension_y_firma('a.bmp', cabecera)

    def test_rechaza_cuando_la_extension_no_corresponde_a_la_firma(self):
        cabecera = _imagen('PNG', 'a.png').read(BYTES_DE_CABECERA)
        with self.assertRaises(serializers.ValidationError):
            validar_extension_y_firma('a.jpg', cabecera)

    def test_rechaza_contenido_que_no_es_imagen(self):
        with self.assertRaises(serializers.ValidationError):
            validar_extension_y_firma('a.png', b'esto no es una imagen')


class CampoImagenSeguraTests(TestCase):
    """Lo que se verifica acá no es solo QUÉ se rechaza, sino CUÁNDO.

    La protección real es que la firma se compruebe antes de que Pillow abra el archivo. Un test
    que solo mirara el código de respuesta pasaría igual con la comprobación puesta después, que es
    justamente la versión que no protege de nada.
    """

    class _Serializer(serializers.Serializer):
        avatar = CampoImagenSegura()

    def test_un_bmp_renombrado_a_png_no_llega_al_plugin_de_pillow(self):
        invocaciones = []
        original = BmpImagePlugin.BmpImageFile._open

        def espia(self, *args, **kwargs):
            invocaciones.append('BmpImagePlugin')
            return original(self, *args, **kwargs)

        BmpImagePlugin.BmpImageFile._open = espia
        try:
            contenido = _imagen('BMP', 'avatar.png').read()
            serializer = self._Serializer(data={'avatar': SimpleUploadedFile('avatar.png', contenido)})
            self.assertFalse(serializer.is_valid())
        finally:
            BmpImagePlugin.BmpImageFile._open = original

        self.assertEqual(invocaciones, [], 'Pillow abrió el archivo pese a que la firma no estaba permitida')

    def test_acepta_un_png_legitimo(self):
        serializer = self._Serializer(data={'avatar': _imagen('PNG', 'avatar.png')})
        self.assertTrue(serializer.is_valid(), serializer.errors)
