import re

from django.core.exceptions import ValidationError

from .catalog import ALLOWED_BORDER_RADII, FONT_FAMILIES

_HEX_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
_FONT_SIZE_RE = re.compile(r'^\d{1,2}px$')


def validate_hex_color(value):
    if value and not _HEX_RE.match(value):
        raise ValidationError(f'"{value}" no es un color hexadecimal válido (#RGB o #RRGGBB).')


def validate_font_slug(value):
    if value not in {f['slug'] for f in FONT_FAMILIES}:
        raise ValidationError(f'"{value}" no es una fuente reconocida.')


def validate_border_radius_slug(value):
    if value not in {r['slug'] for r in ALLOWED_BORDER_RADII}:
        raise ValidationError(f'"{value}" no es un radio de borde reconocido.')


def validate_font_size(value):
    if not _FONT_SIZE_RE.match(value or ''):
        raise ValidationError(f'"{value}" no es un tamaño de fuente válido (ej. "16px").')
