from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path('api/cartera/', include('cartera.urls')),
    path('api/dashboards/', include('cartera.dashboard_urls')),
    # --- Integración skelleton_base (docs/integracion/) -------------------------
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/roles/', include('apps.roles.urls')),
    path('api/permissions/', include('apps.permissions.urls')),
    path('api/branding/', include('apps.branding.urls')),
    path('api/audit/', include('apps.audit.urls')),
]

# El admin de Django solo se publica en desarrollo. En producción era un segundo camino de
# autenticación que evitaba TODAS las defensas propias a la vez: no cuenta intentos fallidos en
# `LoginAttempt` ni aplica el bloqueo temporal, no escribe `LOGIN_SUCCESS`/`LOGIN_FAILED` en la
# auditoría, y crea una sesión de cookie de Django que el modelo `Session` propio no conoce — así
# que "cerrar todas las sesiones" (`SessionService.revocar_todas`) no la tocaba. Toda la
# administración real vive en la API + el frontend (`/admin/*`), que sí auditan y validan
# permisos. `User` además ya no se registra en el admin en ningún entorno (ver
# `apps/users/admin.py`).
if settings.DEBUG:
    from django.contrib import admin

    urlpatterns += [path('admin/', admin.site.urls)]
    # En producción, un servidor web (nginx/etc.) sirve /media/ directamente, Django nunca
    # debería hacerlo. Necesario para el avatar de usuario (`apps.users.models.User.avatar`).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
