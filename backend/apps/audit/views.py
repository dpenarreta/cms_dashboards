from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action

from apps.permissions.permissions import require_permission
from cartera.services import export_service

from .filters import filter_audit_events
from .models import AuditEvent
from .serializers import AuditEventDetailSerializer, AuditEventListSerializer

EXPORT_ROW_LIMIT = 5000

COLUMNAS_EXPORT = [
    ('created_at', 'Fecha y hora'),
    ('domain', 'Dominio'),
    ('action', 'Acción'),
    ('result', 'Resultado'),
    ('severity', 'Severidad'),
    ('actor_username', 'Usuario'),
    ('entity_type', 'Tipo de entidad'),
    ('entity_id', 'Entidad'),
    ('dashboard_id', 'Dashboard'),
    ('component_id', 'Componente'),
    ('ip_address', 'Dirección IP'),
    ('message', 'Descripción'),
]

ACTION_PERMISSION_CLASSES = {
    'list': [require_permission('auditoria.ver')],
    'retrieve': [require_permission('auditoria.ver')],
    'export': [require_permission('auditoria.exportar')],
}


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Solo lectura: la auditoría es append-only (la escribe `apps.audit.services.log_event`,
    nunca esta vista)."""

    queryset = AuditEvent.objects.all()

    def get_permissions(self):
        clases = ACTION_PERMISSION_CLASSES.get(self.action, [require_permission('auditoria.ver')])
        return [clase() for clase in clases]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AuditEventDetailSerializer
        return AuditEventListSerializer

    def get_queryset(self):
        return filter_audit_events(super().get_queryset(), self.request.query_params)

    @action(detail=False, methods=['get'])
    def export(self, request):
        queryset = self.get_queryset()[:EXPORT_ROW_LIMIT]
        filas = [
            {
                'created_at': e.created_at.isoformat(),
                'domain': e.domain,
                'action': e.action,
                'result': e.result,
                'severity': e.severity,
                'actor_username': e.actor_username,
                'entity_type': e.entity_type,
                'entity_id': e.entity_id,
                'dashboard_id': e.dashboard_id,
                'component_id': e.component_id,
                'ip_address': e.ip_address or '',
                'message': e.message,
            }
            for e in queryset
        ]
        buffer = export_service.generar_csv(filas, COLUMNAS_EXPORT)
        respuesta = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
        respuesta['Content-Disposition'] = 'attachment; filename="auditoria.csv"'
        return respuesta
