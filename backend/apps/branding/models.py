from django.db import models

from apps.core.models import BaseModel

from .catalog import DEFAULT_THEME
from .validators import validate_border_radius_slug, validate_font_size, validate_font_slug, validate_hex_color


class SiteTheme(BaseModel):
    """Configuración institucional consolidada (singleton: siempre `pk=1`). La landing, el login
    y el panel autenticado deben leer todos de aquí — única fuente de verdad de identidad
    institucional (sección 16 del prompt de integración)."""

    site_name = models.CharField(max_length=150, default=DEFAULT_THEME['site_name'])
    short_name = models.CharField(max_length=50, blank=True, default=DEFAULT_THEME['short_name'])
    logo_url = models.CharField(max_length=500, blank=True, default=DEFAULT_THEME['logo_url'])
    favicon_url = models.CharField(max_length=500, blank=True, default=DEFAULT_THEME['favicon_url'])

    color_primary = models.CharField(max_length=7, default=DEFAULT_THEME['color_primary'], validators=[validate_hex_color])
    color_secondary = models.CharField(max_length=7, default=DEFAULT_THEME['color_secondary'], validators=[validate_hex_color])
    color_background = models.CharField(max_length=7, default=DEFAULT_THEME['color_background'], validators=[validate_hex_color])
    color_headings = models.CharField(max_length=7, default=DEFAULT_THEME['color_headings'], validators=[validate_hex_color])
    color_text = models.CharField(max_length=7, default=DEFAULT_THEME['color_text'], validators=[validate_hex_color])
    color_links = models.CharField(max_length=7, default=DEFAULT_THEME['color_links'], validators=[validate_hex_color])
    color_buttons = models.CharField(max_length=7, default=DEFAULT_THEME['color_buttons'], validators=[validate_hex_color])
    color_menu = models.CharField(max_length=7, default=DEFAULT_THEME['color_menu'], validators=[validate_hex_color])
    color_success = models.CharField(max_length=7, default=DEFAULT_THEME['color_success'], validators=[validate_hex_color])
    color_danger = models.CharField(max_length=7, default=DEFAULT_THEME['color_danger'], validators=[validate_hex_color])
    color_warning = models.CharField(max_length=7, default=DEFAULT_THEME['color_warning'], validators=[validate_hex_color])
    color_info = models.CharField(max_length=7, default=DEFAULT_THEME['color_info'], validators=[validate_hex_color])
    color_button_text = models.CharField(max_length=7, default=DEFAULT_THEME['color_button_text'], validators=[validate_hex_color])

    font_primary = models.CharField(max_length=20, default=DEFAULT_THEME['font_primary'], validators=[validate_font_slug])
    font_secondary = models.CharField(max_length=20, default=DEFAULT_THEME['font_secondary'], validators=[validate_font_slug])
    font_size_base = models.CharField(max_length=10, default=DEFAULT_THEME['font_size_base'], validators=[validate_font_size])
    border_radius = models.CharField(max_length=20, default=DEFAULT_THEME['border_radius'], validators=[validate_border_radius_slug])

    def save(self, *args, **kwargs):
        # Fuerza el singleton a pk=1. Siempre usar `get_solo()` para obtener la instancia antes de
        # modificarla y guardarla — construir un `SiteTheme(...)` nuevo a mano y guardarlo pisaría
        # la fila existente sin conservar su `created_at` original.
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NotImplementedError('La configuración institucional no se elimina, se restablece.')

    @classmethod
    def get_solo(cls):
        instancia, _ = cls.objects.get_or_create(pk=1, defaults=DEFAULT_THEME)
        return instancia

    def restablecer(self):
        for campo, valor in DEFAULT_THEME.items():
            setattr(self, campo, valor)
        self.save()

    def __str__(self):
        return self.site_name
