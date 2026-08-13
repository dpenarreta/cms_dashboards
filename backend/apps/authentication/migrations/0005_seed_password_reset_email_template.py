"""Crea la fila `EmailTemplate(key='password_reset')` (si no existe) sembrada con el HTML que
antes vivía en `templates/authentication/password_reset_email.html` (ahora eliminado, ver
`apps/authentication/email_template_defaults.py`) — para que activar plantillas de correo
editables no cambie el correo que reciben los usuarios el día 1, mismo criterio que
`apps/branding/migrations/0002_seed_default_theme.py`."""

from django.db import migrations

from apps.authentication.email_template_defaults import DEFAULT_EMAIL_TEMPLATES


def sembrar_plantilla_password_reset(apps, schema_editor):
    EmailTemplate = apps.get_model('authentication', 'EmailTemplate')
    defecto = DEFAULT_EMAIL_TEMPLATES['password_reset']
    EmailTemplate.objects.get_or_create(
        key='password_reset',
        defaults={'subject': defecto['subject'], 'html_body': defecto['html_body']},
    )


def no_revertir(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0004_emailtemplate'),
    ]

    operations = [
        migrations.RunPython(sembrar_plantilla_password_reset, no_revertir),
    ]
