from rest_framework.routers import DefaultRouter

from .views import UserAdminViewSet

router = DefaultRouter()
router.register('', UserAdminViewSet, basename='user-admin')

urlpatterns = router.urls
