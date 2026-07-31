from django.contrib.auth.models import Group
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.permissions.catalog import PERMISSION_CATALOG
from apps.permissions.permissions import require_permission

from .serializers import RoleSerializer, RoleWriteSerializer

ACTION_PERMISSION_CLASSES = {
    'list': [require_permission('roles.ver')],
    'retrieve': [require_permission('roles.ver')],
    'permissions_catalog': [require_permission('roles.ver')],
    'create': [require_permission('roles.editar')],
    'update': [require_permission('roles.editar')],
    'partial_update': [require_permission('roles.editar')],
    'destroy': [require_permission('roles.editar')],
}


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by('name')

    def get_permissions(self):
        clases = ACTION_PERMISSION_CLASSES.get(self.action, [require_permission('roles.ver')])
        return [clase() for clase in clases]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RoleWriteSerializer
        return RoleSerializer

    def perform_create(self, serializer):
        rol = serializer.save()
        log_event(
            domain=AuditEvent.Domain.ROLE_MANAGEMENT, action='ROLE_CREATED', actor=self.request.user,
            entity_type='role', entity_id=rol.id, entity_name=rol.name, new_values={'name': rol.name},
        )

    def perform_update(self, serializer):
        rol = serializer.save()
        log_event(
            domain=AuditEvent.Domain.ROLE_MANAGEMENT, action='ROLE_UPDATED', actor=self.request.user,
            entity_type='role', entity_id=rol.id, entity_name=rol.name, new_values={'name': rol.name},
        )

    def perform_destroy(self, instance):
        log_event(
            domain=AuditEvent.Domain.ROLE_MANAGEMENT, action='ROLE_DELETED', actor=self.request.user,
            entity_type='role', entity_id=instance.id, entity_name=instance.name,
            previous_values={'name': instance.name},
        )
        instance.delete()

    @action(detail=False, methods=['get'], url_path='permissions-catalog')
    def permissions_catalog(self, request):
        agrupado = {}
        for permiso in PERMISSION_CATALOG:
            agrupado.setdefault(permiso['module'], []).append({'codename': permiso['codename'], 'name': permiso['name']})
        return Response({'modules': agrupado})
