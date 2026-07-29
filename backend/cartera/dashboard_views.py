from rest_framework.response import Response
from rest_framework.views import APIView

from . import permisos
from .exceptions import CarteraError
from .models import DashboardAuditLog
from .services import dashboard_layout as dl


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
        layout = dl.aplicar_layout(dashboard_id, componentes, changed_by)

        return Response(dl.serializar_layout(layout))


class DashboardLayoutResetView(APIView):
    def post(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_CONFIGURATION_RESET):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para restablecer el diseño.'}, status=403)

        changed_by = (request.data.get('changed_by') or 'Anónimo')[:150]
        layout = dl.restablecer_layout(dashboard_id, changed_by)
        return Response(dl.serializar_layout(layout))


class DashboardVersionsView(APIView):
    def get(self, request, dashboard_id):
        if not permisos.tiene_permiso(request, permisos.DASHBOARD_VIEW):
            return Response({'error': 'PERMISO_DENEGADO', 'mensaje': 'No tiene permiso para ver este dashboard.'}, status=403)

        entradas = DashboardAuditLog.objects.filter(dashboard_id=dashboard_id)[:50]
        return Response([
            {
                'component_id': e.component_id,
                'change_type': e.change_type,
                'changed_by': e.changed_by,
                'changed_at': e.changed_at.isoformat(),
                'version': e.version,
            }
            for e in entradas
        ])
