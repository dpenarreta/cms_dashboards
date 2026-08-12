from django.db.models import OuterRef, Subquery
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.models import Session
from apps.permissions.permissions import IsSuperuser, require_permission

from .filters import filter_users
from .models import User
from .serializers import (
    PermissionAssignmentSerializer,
    RoleAssignmentSerializer,
    SuperuserAssignmentSerializer,
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
    'reset_password': [require_permission('usuarios.restablecer_password')],
    # Solo otro superusuario puede otorgar/quitar superusuario — ver IsSuperuser.
    'superuser': [IsSuperuser],
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
        # `last_login` (heredado de `AbstractUser`) nunca se completa: el login real emite JWT
        # propio (`AuthenticationService.login`, apps.authentication) sin pasar por
        # `django.contrib.auth.login()`, que es lo único que lo actualiza. `Session.created_at`
        # (una fila nueva por cada login exitoso, ver `SessionService.crear`) es la fuente real de
        # "última conexión" — se anota acá (subquery correlacionada, evita N+1 por usuario) en vez
        # de calcularla en el serializer.
        ultima_sesion = Session.objects.filter(user=OuterRef('pk')).order_by('-created_at')
        queryset = super().get_queryset().annotate(ultima_conexion=Subquery(ultima_sesion.values('created_at')[:1]))
        return filter_users(queryset, self.request.query_params)

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

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        usuario, password_temporal = UserAdminService.reset_password(usuario=self.get_object(), actor=request.user)
        return Response({**UserAdminDetailSerializer(usuario).data, 'temporary_password': password_temporal})

    @action(detail=True, methods=['post'])
    def superuser(self, request, pk=None):
        serializer = SuperuserAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = UserAdminService.set_superuser(
            usuario=self.get_object(), es_superusuario=serializer.validated_data['is_superuser'], actor=request.user,
        )
        return Response(UserAdminDetailSerializer(usuario).data)
