"""Valores por defecto de las plantillas de correo (`EmailTemplate.get_or_seed`/`restablecer`, y
la migración de datos que siembra la fila inicial). El HTML de `password_reset` es el mismo que
antes vivía en `templates/authentication/password_reset_email.html` — se movió acá para que sea
editable desde `/admin/settings`, sin cambiar el correo que reciben los usuarios el día 1.

Variables disponibles (sustitución simple `{{ variable }}`, no motor de templates de Django — ver
`EmailTemplate` y `services.py::_renderizar_plantilla`):
- `nombre_usuario`: `usuario.first_name` o, si está vacío, `usuario.username` (nunca vacío).
- `enlace`: URL completa de recuperación (`FRONTEND_URL` + `/reset-password?token=...`).
- `minutos_expiracion`: minutos de validez del enlace (`PASSWORD_RESET_TOKEN_LIFETIME_MINUTES`).
- `site_name` / `color_primary`: identidad institucional (`apps.branding.SiteTheme`).
"""

_PASSWORD_RESET_HTML = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #eeeeee; padding: 24px;">
  <div style="max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 10px; padding: 32px; border: 1px solid #dddddd;">
    <h1 style="font-size: 20px; color: {{ color_primary }}; margin: 0 0 16px;">{{ site_name }}</h1>
    <p>Hola {{ nombre_usuario }},</p>
    <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en {{ site_name }}.</p>
    <p style="text-align: center; margin: 28px 0;">
      <a href="{{ enlace }}" style="background: {{ color_primary }}; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; display: inline-block;">
        Restablecer contraseña
      </a>
    </p>
    <p style="font-size: 13px; color: #444444;">Si el botón no funciona, copiá y pegá este enlace
      en tu navegador: {{ enlace }}</p>
    <p>Este enlace es válido durante {{ minutos_expiracion }} minutos. Si no lo utilizas en ese
      tiempo, deberás solicitar uno nuevo.</p>
    <p>Si tú no solicitaste este cambio, puedes ignorar este mensaje: tu contraseña actual seguirá
      funcionando y no se realizará ningún cambio.</p>
    <p style="font-size: 12px; color: #666666; margin-top: 32px;">
      Por seguridad, nunca compartas este enlace con nadie. {{ site_name }} nunca te pedirá tu
      contraseña por correo electrónico.
    </p>
  </div>
</body>
</html>
"""

DEFAULT_EMAIL_TEMPLATES = {
    'password_reset': {
        'subject': 'Recuperación de contraseña | {{ site_name }}',
        'html_body': _PASSWORD_RESET_HTML,
    },
}

# Variables disponibles por plantilla — expuestas por `EmailTemplateAdminView.get` para que el
# frontend muestre una leyenda junto al editor (no hace falta un endpoint aparte).
TEMPLATE_VARIABLES = {
    'password_reset': [
        {'name': 'nombre_usuario', 'description': 'Nombre del usuario (o su usuario, si no tiene nombre cargado).'},
        {'name': 'enlace', 'description': 'Enlace único para restablecer la contraseña.'},
        {'name': 'minutos_expiracion', 'description': 'Minutos de validez del enlace.'},
        {'name': 'site_name', 'description': 'Nombre del sitio (identidad institucional).'},
        {'name': 'color_primary', 'description': 'Color principal institucional (hex).'},
    ],
}
