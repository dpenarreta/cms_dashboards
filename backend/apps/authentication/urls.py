from django.urls import path

from . import views

urlpatterns = [
    path('login', views.LoginView.as_view(), name='auth-login'),
    path('token/refresh', views.RefreshView.as_view(), name='auth-token-refresh'),
    path('logout', views.LogoutView.as_view(), name='auth-logout'),
    path('logout-all', views.LogoutAllView.as_view(), name='auth-logout-all'),
    path('me', views.MeView.as_view(), name='auth-me'),
    path('me/avatar', views.MyAvatarView.as_view(), name='auth-me-avatar'),
    path('password/change', views.ChangeOwnPasswordView.as_view(), name='auth-password-change'),
    path('password-reset/request', views.PasswordResetRequestView.as_view(), name='auth-password-reset-request'),
    path('password-reset/validate', views.PasswordResetValidateView.as_view(), name='auth-password-reset-validate'),
    path('password-reset/confirm', views.PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
]
