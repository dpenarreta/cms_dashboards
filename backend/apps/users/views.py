from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.permissions.permissions import require_permission

from .filters import filter_users
from .models import User
from .serializers import (
    PermissionAssignmentSerializer,
    RoleAssignmentSerializer,
    UserAdminCreateSerializer,
    UserAdminDetailSerializer,
    UserAdminListSerializer,
    UserAdminUpdateSerializer,
)
from .services import UserAdminService

ACTION_PERMISSION_CLASSES = {
    'list': [require_permission('usuarios.ver')],
    'retrieve': [require_permission('usuarios.ver')],
    'create': [require_permission('usuarios.crear')],
    'update': [require_permission('usuarios.editar')],
    'partial_update': [require_permission('usuarios.editar')],
    'enable': [require_permission('usuarios.deshabilitar')],
    'disable': [require_permission('usuarios.deshabilitar')],
    'block': [require_permission('usuarios.deshabilitar')],
    'unblock': [require_permission('usuarios.deshabilitar')],
    'roles': [require_permission('usuarios.editar')],
    'permissions': [require_permission('usuarios.editar')],
}


class UserAdminViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('username')
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        clases = ACTION_PERMISSION_CLASSES.get(self.action, [require_permission('usuarios.ver')])
        return [clase() for clase in clases]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserAdminCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserAdminUpdateSerializer
        if self.action == 'retrieve':
            return UserAdminDetailSerializer
        return UserAdminListSerializer

    def get_queryset(self):
        return filter_users(super().get_queryset(), self.request.query_params)

    def perform_create(self, serializer):
        usuario = UserAdminService.create_user(data=serializer.validated_data, created_by=self.request.user)
        serializer.instance = usuario

    def perform_update(self, serializer):
        usuario = UserAdminService.update_user(usuario=serializer.instance, data=serializer.validated_data, updated_by=self.request.user)
        serializer.instance = usuario

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        usuario = UserAdminService.enable(usuario=self.get_object(), actor=request.user)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        usuario = UserAdminService.disable(usuario=self.get_object(), actor=request.user)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        usuario = UserAdminService.block(usuario=self.get_object(), actor=request.user)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        usuario = UserAdminService.unblock(usuario=self.get_object(), actor=request.user)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def roles(self, request, pk=None):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = UserAdminService.assign_roles(
            usuario=self.get_object(), role_ids=serializer.validated_data['role_ids'], actor=request.user,
        )
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'], url_path='permissions')
    def permissions(self, request, pk=None):
        serializer = PermissionAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = UserAdminService.assign_permissions(
            usuario=self.get_object(), codenames=serializer.validated_data['codenames'], actor=request.user,
        )
        return Response(UserAdminDetailSerializer(usuario).data)
