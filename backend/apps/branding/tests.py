from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from .catalog import DEFAULT_THEME
from .models import SiteTheme
from .validators import validate_hex_color

User = get_user_model()


class SiteThemeModelTests(TestCase):
    def test_get_solo_devuelve_la_fila_sembrada_por_la_migracion(self):
        """La migración de datos `0002_seed_default_theme` ya crea la fila `pk=1` al migrar (se
        aplica también sobre la base de pruebas) — `get_solo()` debe devolver esa misma fila, con
        los valores por defecto sembrados desde `dashboard.css`, sin crear una segunda."""
        self.assertEqual(SiteTheme.objects.count(), 1)
        tema = SiteTheme.get_solo()
        self.assertEqual(tema.pk, 1)
        self.assertEqual(tema.site_name, DEFAULT_THEME['site_name'])
        self.assertEqual(tema.color_primary, DEFAULT_THEME['color_primary'])

    def test_es_singleton_pk_siempre_1(self):
        tema = SiteTheme.get_solo()
        tema.site_name = 'Otro nombre'
        tema.save()
        self.assertEqual(SiteTheme.objects.count(), 1)
        self.assertEqual(SiteTheme.objects.get().site_name, 'Otro nombre')

    def test_restablecer_vuelve_a_los_valores_por_defecto(self):
        tema = SiteTheme.get_solo()
        tema.color_primary = '#111111'
        tema.save()
        tema.restablecer()
        tema.refresh_from_db()
        self.assertEqual(tema.color_primary, DEFAULT_THEME['color_primary'])

    def test_no_permite_eliminar(self):
        tema = SiteTheme.get_solo()
        with self.assertRaises(NotImplementedError):
            tema.delete()

    def test_validador_de_color_hex(self):
        validate_hex_color('#1F4E78')
        validate_hex_color('')
        with self.assertRaises(ValidationError):
            validate_hex_color('no-es-un-color')


class ThemeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='Clave-Segura-123')

    def test_tema_actual_es_publico(self):
        resp = self.client.get('/api/branding/current')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['site_name'], DEFAULT_THEME['site_name'])
        self.assertIn('font_primary_css', resp.json())

    def test_admin_requiere_permiso_configuracion_ver(self):
        usuario = User.objects.create_user(username='sin_permiso', email='sp@example.com', password='Clave-Segura-123')
        self.client.force_authenticate(user=usuario)
        resp = self.client.get('/api/branding/admin')
        self.assertEqual(resp.status_code, 403)

    def test_administrador_general_puede_editar_el_tema(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch('/api/branding/admin', {'color_primary': '#123456'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['color_primary'], '#123456')

        publico = self.client.get('/api/branding/current').json()
        self.assertEqual(publico['color_primary'], '#123456')

    def test_rechaza_color_invalido(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch('/api/branding/admin', {'color_primary': 'no-valido'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_restablecer_requiere_configuracion_editar(self):
        usuario = User.objects.create_user(username='solo_ver', email='sv@example.com', password='Clave-Segura-123')
        from django.contrib.auth.models import Permission
        usuario.user_permissions.add(Permission.objects.get(codename='configuracion.ver', content_type__app_label='permissions'))
        self.client.force_authenticate(user=usuario)
        resp = self.client.post('/api/branding/admin/reset')
        self.assertEqual(resp.status_code, 403)

    def test_opciones_de_fuentes_y_radios(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get('/api/branding/admin/options')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.json()['fonts']) > 0)
        self.assertTrue(len(resp.json()['border_radii']) > 0)
