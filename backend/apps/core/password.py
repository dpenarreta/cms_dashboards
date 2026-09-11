"""Punto único de validación de fortaleza de contraseña.

`settings.AUTH_PASSWORD_VALIDATORS` declara los validadores de Django (similitud con los datos del
usuario, longitud mínima, contraseñas comunes y contraseñas solo numéricas), pero Django los
aplica ÚNICAMENTE donde alguien llama a `validate_password` — los serializers de DRF no lo hacen
por su cuenta. Antes de este módulo nadie lo llamaba, así que la única regla real era un
`min_length=8` repetido a mano en cuatro campos y `12345678`, `password` o el propio nombre de
usuario se aceptaban sin objeción.

Se usa como validador de campo de DRF en las cuatro rutas que fijan una contraseña:
`ChangeOwnPasswordSerializer`, `PasswordResetConfirmSerializer` (apps.authentication) y
`UserAdminCreateSerializer` (apps.users), más la contraseña temporal que genera
`UserAdminService.reset_password`.

No usa `CarteraError`: al ser un error de validación de un campo concreto, corresponde el
`ValidationError` de DRF, que el contrato de error global ya traduce a 400 con el detalle por
campo (ver `cartera.exceptions.cartera_exception_handler`, que delega en el handler de DRF cuando
este produce respuesta).
"""

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


def validar_fortaleza(password, usuario=None):
    """Corre los validadores configurados y traduce el error de Django al de DRF.

    `usuario` es opcional pero conviene pasarlo donde exista: `UserAttributeSimilarityValidator`
    solo puede comparar la contraseña contra el username/nombre/correo si recibe la instancia. Sin
    él, ese validador no aporta nada y los otros tres siguen funcionando igual.
    """
    try:
        password_validation.validate_password(password, user=usuario)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))
    return password


def campo_password(**kwargs):
    """Campo de contraseña con la validación de fortaleza ya enganchada.

    Reemplaza el `min_length=8` que estaba repetido en cada serializer: la longitud mínima la
    aporta ahora `MinimumLengthValidator` del catálogo de settings, así que el mínimo se cambia en
    un solo lugar y no puede quedar desalineado entre rutas.
    """
    kwargs.setdefault('trim_whitespace', False)
    return serializers.CharField(validators=[validar_fortaleza], **kwargs)
