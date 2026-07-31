from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
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
