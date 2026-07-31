from django.urls import path

from . import views

urlpatterns = [
    path('', views.PermissionCatalogView.as_view(), name='permission-catalog'),
]
