from django.urls import path

from . import dashboard_views

urlpatterns = [
    path('', dashboard_views.DashboardCreateView.as_view(), name='dashboards-create'),
    path('authorized', dashboard_views.DashboardsAuthorizedView.as_view(), name='dashboards-authorized'),
    path('<slug:dashboard_id>/layout', dashboard_views.DashboardLayoutView.as_view(), name='dashboard-layout'),
    path('<slug:dashboard_id>/layout/reset', dashboard_views.DashboardLayoutResetView.as_view(), name='dashboard-layout-reset'),
    path('<slug:dashboard_id>/versions', dashboard_views.DashboardVersionsView.as_view(), name='dashboard-versions'),
    path('<slug:dashboard_id>/', dashboard_views.DashboardDetailView.as_view(), name='dashboard-detail'),
]
