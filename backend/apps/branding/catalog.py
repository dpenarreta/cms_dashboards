"""Catálogo de opciones de tipografía/radio de bordes + valores por defecto del tema.

`DEFAULT_THEME` se sembró a partir de la paleta que ya usa `frontend/src/styles/dashboard.css`
(colores `--series-1`/`--page-plane`/`--text-primary`, radio de 10px de `.chart-panel`/`.kpi-card`)
para que activar `apps.branding` no cambie la identidad visual existente el día 1 — ver
docs/integracion/decisions.md.
"""

# 17 opciones (una misma lista sirve para "fuente principal" y "fuente secundaria" — mismo
# selector, `SettingsPage.jsx`), todas con pila de fuentes del sistema (sin cargar ningún web
# font externo: ni `<link>` a Google Fonts ni `@font-face` en ningún lado del frontend — 'inter'
# ya seguía este mismo criterio antes de esta lista, se deja igual). El slug es lo único que se
# persiste (`SiteTheme.font_primary/font_secondary`, `max_length=20`) — mantenerlos cortos.
FONT_FAMILIES = [
    {'slug': 'system', 'label': 'Sistema (por defecto)', 'css': "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"},
    {'slug': 'inter', 'label': 'Inter', 'css': "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"},
    {'slug': 'arial', 'label': 'Arial', 'css': "Arial, Helvetica, sans-serif"},
    {'slug': 'verdana', 'label': 'Verdana', 'css': "Verdana, Geneva, sans-serif"},
    {'slug': 'tahoma', 'label': 'Tahoma', 'css': "Tahoma, Geneva, sans-serif"},
    {'slug': 'trebuchet', 'label': 'Trebuchet MS', 'css': "'Trebuchet MS', Helvetica, sans-serif"},
    {'slug': 'segoe', 'label': 'Segoe UI', 'css': "'Segoe UI', Tahoma, Geneva, sans-serif"},
    {'slug': 'calibri', 'label': 'Calibri', 'css': "Calibri, Candara, Segoe, sans-serif"},
    {'slug': 'century-gothic', 'label': 'Century Gothic', 'css': "'Century Gothic', CenturyGothic, AppleGothic, sans-serif"},
    {'slug': 'gill-sans', 'label': 'Gill Sans', 'css': "'Gill Sans', 'Gill Sans MT', Calibri, sans-serif"},
    {'slug': 'georgia', 'label': 'Georgia', 'css': "Georgia, 'Times New Roman', serif"},
    {'slug': 'times', 'label': 'Times New Roman', 'css': "'Times New Roman', Times, serif"},
    {'slug': 'garamond', 'label': 'Garamond', 'css': "Garamond, 'Palatino Linotype', serif"},
    {'slug': 'palatino', 'label': 'Palatino', 'css': "'Palatino Linotype', 'Book Antiqua', Palatino, serif"},
    {'slug': 'cambria', 'label': 'Cambria', 'css': "Cambria, Georgia, serif"},
    {'slug': 'courier', 'label': 'Courier New', 'css': "'Courier New', Courier, monospace"},
    {'slug': 'consolas', 'label': 'Consolas', 'css': "Consolas, 'Courier New', monospace"},
]

ALLOWED_BORDER_RADII = [
    {'slug': 'small', 'label': 'Pequeño', 'css': '6px'},
    {'slug': 'medium', 'label': 'Mediano', 'css': '10px'},
    {'slug': 'large', 'label': 'Grande', 'css': '16px'},
]

DEFAULT_THEME = {
    'site_name': 'Dashboard de Cartera',
    'short_name': 'Cartera',
    'logo_url': '',
    'favicon_url': '',
    'color_primary': '#2a78d6',
    'color_secondary': '#eb6834',
    'color_background': '#eeeeee',
    'color_headings': '#000000',
    'color_text': '#000000',
    'color_links': '#2a78d6',
    'color_buttons': '#2a78d6',
    'color_menu': '#ffffff',
    # Paleta semántica estándar de Bootstrap 5 (sección 16 / Módulo B, integración visual con
    # Bootstrap) — se usan como valor por defecto para no romper el aspecto de `success`/`danger`/
    # `warning`/`info` ya conocido por los usuarios al activar esta configuración el día 1.
    'color_success': '#198754',
    'color_danger': '#dc3545',
    'color_warning': '#ffc107',
    'color_info': '#0dcaf0',
    'color_button_text': '#ffffff',
    'font_primary': 'system',
    'font_secondary': 'system',
    'font_size_base': '16px',
    'border_radius': 'medium',
}


def font_css(slug):
    return next((f['css'] for f in FONT_FAMILIES if f['slug'] == slug), FONT_FAMILIES[0]['css'])


def border_radius_css(slug):
    return next((r['css'] for r in ALLOWED_BORDER_RADII if r['slug'] == slug), ALLOWED_BORDER_RADII[1]['css'])
