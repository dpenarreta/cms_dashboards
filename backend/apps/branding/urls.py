from django.urls import path

from . import views

urlpatterns = [
    path('current', views.CurrentThemeView.as_view(), name='branding-current'),
    path('admin', views.ThemeAdminView.as_view(), name='branding-admin'),
    path('admin/reset', views.ThemeResetView.as_view(), name='branding-admin-reset'),
    path('admin/options', views.ThemeOptionsView.as_view(), name='branding-admin-options'),
]
