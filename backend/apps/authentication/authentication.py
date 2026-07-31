from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .models import Session


class SessionAuthentication(JWTAuthentication):
    """Envuelve `JWTAuthentication`: exige el claim `sid` y valida que la `Session` asociada
    siga activa (no revocada, no expirada) además de la validación estándar de `user.is_active`
    que ya hace la clase base."""

    def get_user(self, validated_token):
        sid = validated_token.get('sid')
        if not sid:
            raise AuthenticationFailed('El token no corresponde a una sesión válida.')
        try:
            sesion = Session.objects.select_related('user').get(id=sid)
        except (Session.DoesNotExist, ValueError):
            raise AuthenticationFailed('La sesión ya no existe.')
        if not sesion.is_active:
            raise AuthenticationFailed('La sesión expiró o fue revocada.')
        usuario = super().get_user(validated_token)
        sesion.save(update_fields=['last_used_at'])
        return usuario
