from django.urls import path

from . import dashboard_views

urlpatterns = [
    path('<slug:dashboard_id>/layout', dashboard_views.DashboardLayoutView.as_view(), name='dashboard-layout'),
    path('<slug:dashboard_id>/layout/reset', dashboard_views.DashboardLayoutResetView.as_view(), name='dashboard-layout-reset'),
    path('<slug:dashboard_id>/versions', dashboard_views.DashboardVersionsView.as_view(), name='dashboard-versions'),
]
