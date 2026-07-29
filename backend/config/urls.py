from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/cartera/', include('cartera.urls')),
    path('api/dashboards/', include('cartera.dashboard_urls')),
]
