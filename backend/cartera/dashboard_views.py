from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditEvent
from apps.permissions.permissions import require_permission

from . import dashboard_registry, permisos
from .exceptions import CarteraError
from .services import dashboard_layout as dl
from .services import dashboards as dashboards_service


def _permisos_respuesta(request):
    return permisos.permisos_del_usuario(request)


class DashboardLayoutView(APIView):
    def get(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)

        layout = dl.obtener_o_crear_layout(dashboard_id)
        return Response({**dl.serializar_layout(layout), 'permisos': _permisos_respuesta(request)})

    def put(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_LAYOUT_EDIT):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para editar el layout.'}, status=403)

        version_recibida = request.data.get('version')
        if version_recibida is None:
            raise CarteraError('Se requiere la versión del layout que se está editando.', codigo='VERSION_REQUERIDA')

        layout_actual = dl.obtener_o_crear_layout(dashboard_id)
        if int(version_recibida) != layout_actual.version:
            return Response({
                'error': 'CONFLICTO_DE_VERSION',
                'mensaje': 'Existe una versión más reciente de este dashboard. Recargue antes de guardar.',
                **dl.serializar_layout(layout_actual),
            }, status=409)

        componentes = dl.validar_componentes(dashboard_id, request.data.get('components') or [])
        changed_by = (request.data.get('changed_by') or 'Anónimo')[:150]
        layout = dl.aplicar_layout(dashboard_id, componentes, changed_by, actor=request.user, request=request)

        return Response(dl.serializar_layout(layout))


class DashboardLayoutResetView(APIView):
    def post(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_CONFIGURATION_RESET):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para restablecer el diseño.'}, status=403)

        changed_by = (request.data.get('changed_by') or 'Anónimo')[:150]
        layout = dl.restablecer_layout(dashboard_id, changed_by, actor=request.user, request=request)
        return Response(dl.serializar_layout(layout))


class DashboardsAuthorizedView(APIView):
    """`GET /api/dashboards/authorized` — solo los dashboards que el usuario autenticado puede
    ver (nunca hardcodeado en el frontend, sección 13 de la integración con skelleton_base)."""

    def get(self, request):
        return Response(dashboard_registry.dashboards_autorizados(request))


class DashboardCreateView(APIView):
    """`POST /api/dashboards/` — crea un dashboard nuevo por área (solo el contenedor: nombre,
    área y un `dashboard_id` único generado a partir del nombre; sin procesamiento de datos
    propio, alcance acotado explícitamente por el usuario)."""

    permission_classes = [require_permission(permisos.DASHBOARD_CREAR)]

    def post(self, request):
        dashboard = dashboards_service.crear_dashboard(
            nombre=request.data.get('name'),
            area=request.data.get('area', ''),
            descripcion=request.data.get('description', ''),
            creado_por=request.user,
            request=request,
        )
        return Response({
            'dashboard_id': dashboard.dashboard_id, 'name': dashboard.name, 'area': dashboard.area,
            'description': dashboard.description,
        }, status=201)


class DashboardDetailView(APIView):
    """`PATCH`/`DELETE /api/dashboards/<dashboard_id>/` — edición (nombre/área) y eliminación de
    un dashboard por área."""

    def patch(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_EDITAR):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para editar dashboards.'}, status=403)

        dashboard = dashboards_service.actualizar_dashboard(
            dashboard_id, nombre=request.data.get('name'), area=request.data.get('area', ''),
            actor=request.user, request=request,
        )
        return Response({'dashboard_id': dashboard.dashboard_id, 'name': dashboard.name, 'area': dashboard.area})

    def delete(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_ELIMINAR):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para eliminar dashboards.'}, status=403)

        dashboards_service.eliminar_dashboard(
            dashboard_id, confirmacion_nombre=request.data.get('confirmation_name', ''),
            actor=request.user, request=request,
        )
        return Response(status=204)


class DashboardVersionsView(APIView):
    def get(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)

        entradas = AuditEvent.objects.filter(
            domain__in=[AuditEvent.Domain.DASHBOARD_LAYOUT, AuditEvent.Domain.DASHBOARD_CONFIGURATION],
            dashboard_id=dashboard_id,
        )[:50]
        return Response([
            {
                'component_id': e.component_id,
                'change_type': e.action,
                'changed_by': e.metadata.get('changed_by_label') or e.actor_username or 'Anónimo',
                'changed_at': e.created_at.isoformat(),
                'version': e.metadata.get('version'),
            }
            for e in entradas
        ])
