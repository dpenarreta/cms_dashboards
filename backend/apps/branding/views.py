from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.permissions.permissions import require_permission

from .catalog import ALLOWED_BORDER_RADII, FONT_FAMILIES
from .models import SiteTheme
from .serializers import SiteThemeSerializer, SiteThemeUpdateSerializer


class CurrentThemeView(APIView):
    """Pública: login/landing también deben poder pintarse con la marca configurada, sin sesión."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(SiteThemeSerializer(SiteTheme.get_solo()).data)


class ThemeAdminView(APIView):
    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [require_permission('configuracion.editar')()]
        return [require_permission('configuracion.ver')()]

    def get(self, request):
        return Response(SiteThemeSerializer(SiteTheme.get_solo()).data)

    def patch(self, request):
        tema = SiteTheme.get_solo()
        anterior = SiteThemeSerializer(tema).data
        serializer = SiteThemeUpdateSerializer(tema, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_event(
            domain=AuditEvent.Domain.SYSTEM_CONFIGURATION, action='BRANDING_UPDATED', actor=request.user,
            entity_type='site_theme', entity_id=tema.pk, request=request,
            previous_values=anterior, new_values=serializer.validated_data,
        )
        return Response(SiteThemeSerializer(tema).data)


class ThemeResetView(APIView):
    permission_classes = [require_permission('configuracion.editar')]

    def post(self, request):
        tema = SiteTheme.get_solo()
        tema.restablecer()
        log_event(
            domain=AuditEvent.Domain.SYSTEM_CONFIGURATION, action='BRANDING_RESET', actor=request.user,
            entity_type='site_theme', entity_id=tema.pk, request=request,
        )
        return Response(SiteThemeSerializer(tema).data)


class ThemeOptionsView(APIView):
    permission_classes = [require_permission('configuracion.ver')]

    def get(self, request):
        return Response({'fonts': FONT_FAMILIES, 'border_radii': ALLOWED_BORDER_RADII})
