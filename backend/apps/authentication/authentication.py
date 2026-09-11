from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from .models import Session

# `last_used_at` se refresca como máximo una vez por minuto y por sesión. Antes se escribía en
# CADA petición autenticada: una pantalla de dashboard que dispara doce llamadas producía doce
# UPDATE contra SQL Server dentro del camino de autenticación. Además de costar rendimiento, daba
# amplificación (peticiones baratas para el cliente, escrituras para el servidor). Con un minuto
# de granularidad el dato sigue sirviendo para "última actividad" sin escribir por petición.
INTERVALO_REFRESCO_USO_SEGUNDOS = 60


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
        # La sesión se emite para un usuario concreto: que el `sid` y el `user_id` del token
        # apunten a distinta cuenta no debería poder ocurrir (los dos claims van firmados juntos),
        # pero comprobarlo es gratis y convierte un error de emisión futuro en un 401 en vez de en
        # una confusión de identidad.
        if sesion.user_id != usuario.id:
            raise AuthenticationFailed('El token no corresponde a una sesión válida.')
        self._refrescar_uso(sesion)
        return usuario

    @staticmethod
    def _refrescar_uso(sesion):
        ahora = timezone.now()
        if sesion.last_used_at and (ahora - sesion.last_used_at).total_seconds() < INTERVALO_REFRESCO_USO_SEGUNDOS:
            return
        # `update(...)` en vez de `save()`: `last_used_at` es `auto_now=True`, así que un `save`
        # parcial reescribiría el campo igual, pero esto evita traer y volver a escribir la fila
        # completa y no dispara señales de modelo.
        Session.objects.filter(pk=sesion.pk).update(last_used_at=ahora)
