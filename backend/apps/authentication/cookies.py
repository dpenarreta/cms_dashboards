"""Cookie `HttpOnly` que transporta el refresh token (SEC-19).

Antes el refresh token se devolvía en el cuerpo de `POST /api/auth/login` y el frontend lo guardaba
en `localStorage`. Eso significaba que cualquier XSS podía leerlo y llevárselo: una credencial de 7
días, utilizable desde otra máquina, mucho después de que la víctima cerrara la pestaña.

En una cookie `HttpOnly` el token sigue existiendo, pero JavaScript no puede leerlo. La ganancia es
acotada y conviene tenerla clara: un XSS todavía puede actuar como el usuario dentro de la sesión
(tiene el access token y puede llamar a la API). Lo que ya no puede es EXFILTRAR una credencial de
larga duración para usarla por fuera. Ese es exactamente el riesgo que este cambio elimina.

Tres decisiones que sostienen la protección, todas en `settings.py`:

- `path=/api/auth` — la cookie no se manda en ninguna otra petición de la API.
- `SameSite=Lax` — el navegador no la manda en un POST originado en otro sitio, que es lo que
  protege al endpoint de refresco de un CSRF sin necesidad de un token anti-CSRF aparte.
- `Secure` fuera de desarrollo.
"""

from django.conf import settings


def _vida_en_segundos():
    return int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds())


def poner_refresh(response, refresh_token):
    """Deja el refresh token en la cookie. Sin `refresh_token`, no hace nada."""
    if not refresh_token:
        return response
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=_vida_en_segundos(),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )
    return response


def quitar_refresh(response):
    """Borra la cookie. El `path` tiene que coincidir con el del `set_cookie` o el navegador la
    conserva: una cookie se identifica por (nombre, dominio, path), no solo por su nombre."""
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
    return response


def leer_refresh(request, del_cuerpo=None):
    """Refresh token de la petición: primero la cookie, y si no está, el cuerpo.

    El respaldo por cuerpo es TRANSITORIO y cubre un caso concreto del despliegue: una pestaña que
    ya estaba abierta sigue ejecutando el JavaScript VIEJO, que manda el refresh en el cuerpo y no
    sabe nada de la cookie. Sin el respaldo, esa pestaña se rompe en cuanto vence su access token;
    con él, sigue andando hasta que la persona recargue.

    Lo que el respaldo NO hace es evitar que haya que volver a iniciar sesión: el frontend nuevo
    borra el token heredado de `localStorage` al arrancar y nunca lo manda, así que quien recargue
    la página entra con el flujo de cookie desde cero. Es un reinicio de sesión de una sola vez.

    Se puede quitar pasada la vigencia del refresh token (7 días por defecto) desde el despliegue.
    """
    return request.COOKIES.get(settings.REFRESH_COOKIE_NAME) or del_cuerpo or None
