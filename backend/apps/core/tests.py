from django.test import TestCase

from .audit import mask_sensitive_fields


class MaskSensitiveFieldsTests(TestCase):
    def test_enmascara_claves_sensibles_sin_tocar_el_resto(self):
        resultado = mask_sensitive_fields({'username': 'ana', 'password': 'secreta123', 'refresh_token': 'abc.def.ghi'})
        self.assertEqual(resultado['username'], 'ana')
        self.assertEqual(resultado['password'], '***')
        self.assertEqual(resultado['refresh_token'], '***')

    def test_valores_no_diccionario_se_devuelven_igual(self):
        self.assertEqual(mask_sensitive_fields(None), None)
        self.assertEqual(mask_sensitive_fields('texto'), 'texto')
