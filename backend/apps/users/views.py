from django.db.models import OuterRef, Subquery
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.authentication.models import Session
from apps.permissions.authorization import get_user_permission_codenames
from apps.permissions.permissions import IsSuperuser, require_permission
from cartera.exceptions import CarteraError

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


def _rechazar_si_es_uno_mismo(actor, objetivo, accion):
    """Impide que alguien aplique sobre su propia cuenta las acciones que conceden privilegios.

    Sin esta guarda, `usuarios.editar` equivalía al catálogo completo: bastaba con hacer POST a
    `/api/users/<propio-id>/permissions` con todos los codenames, o asignarse un rol que los
    tenga. Es el mismo razonamiento por el que `superuser` exige `IsSuperuser` (ver
    `apps/permissions/permissions.py::IsSuperuser`): un permiso asignable no debe poder ampliarse
    a sí mismo. Otorgar privilegios a otra persona sigue permitido — lo que se corta es el
    auto-otorgamiento.
    """
    if actor is not None and objetivo.pk == actor.pk:
        raise CarteraError(
            f'No puede {accion} sobre su propia cuenta. Pídalo a otro administrador.',
            codigo='AUTO_MODIFICACION_NO_PERMITIDA',
        )


def _codenames_que_puede_otorgar(actor, codenames):
    """Nadie concede un permiso que él mismo no tiene.

    Antes, `assign_permissions` aceptaba cualquier codename del catálogo, así que quien tenía
    `usuarios.editar` podía otorgar los 30 permisos del sistema a la cuenta que quisiera —
    incluido, por interpósita persona, a un cómplice. Un superusuario mantiene el catálogo
    completo (`get_user_permission_codenames` se lo devuelve entero), así que para él esto no
    cambia nada; para todos los demás, la delegación queda acotada a lo que se les otorgó.

    Rechaza en vez de recortar en silencio: pedir un permiso que no se puede dar es un error del
    llamador, y aplicar una lista distinta de la enviada dejaría al frontend mostrando algo que no
    ocurrió.
    """
    solicitados = set(codenames)
    propios = get_user_permission_codenames(actor)
    excedidos = sorted(solicitados - propios)
    if excedidos:
        raise CarteraError(
            'No puede otorgar permisos que usted no tiene: ' + ', '.join(excedidos),
            codigo='PERMISO_NO_DELEGABLE',
            detalles={'codenames': excedidos},
        )
    return codenames


def _rechazar_si_el_objetivo_es_superusuario(actor, objetivo, accion):
    """Reserva al superusuario cualquier acción sobre una cuenta superusuario.

    `reset_password` devolvía la contraseña temporal en la respuesta y aceptaba un superusuario
    como objetivo, así que un permiso asignable (`usuarios.restablecer_password`) alcanzaba para
    tomar la cuenta `admin` en tres pasos. `disable`/`block` sobre un superusuario son el mismo
    problema en su versión destructiva: dejar al administrador fuera del sistema.
    """
    if objetivo.is_superuser and not (actor is not None and actor.is_superuser):
        raise CarteraError(
            f'Solo un superusuario puede {accion} sobre otra cuenta superusuario.',
            codigo='OBJETIVO_SUPERUSUARIO',
        )


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
        usuario = UserAdminService.create_user(data=serializer.validated_data, created_by=self.request.user, request=self.request)
        serializer.instance = usuario

    def perform_update(self, serializer):
        # `UserAdminUpdateSerializer` incluye `email`, y el correo es lo que gobierna la
        # recuperación de contraseña: sin esta guarda, alguien con `usuarios.editar` podía
        # apuntar el correo de un superusuario a su propio buzón, pedir el enlace de recuperación
        # y quedarse con la cuenta — la misma toma de control que `reset_password`, por otra
        # puerta.
        _rechazar_si_el_objetivo_es_superusuario(self.request.user, serializer.instance, 'editar los datos')
        usuario = UserAdminService.update_user(usuario=serializer.instance, data=serializer.validated_data, updated_by=self.request.user, request=self.request)
        serializer.instance = usuario

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        usuario = UserAdminService.enable(usuario=self.get_object(), actor=request.user, request=request)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        objetivo = self.get_object()
        _rechazar_si_el_objetivo_es_superusuario(request.user, objetivo, 'deshabilitar una cuenta')
        usuario = UserAdminService.disable(usuario=objetivo, actor=request.user, request=request)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def block(self, request, pk=None):
        objetivo = self.get_object()
        _rechazar_si_el_objetivo_es_superusuario(request.user, objetivo, 'bloquear una cuenta')
        usuario = UserAdminService.block(usuario=objetivo, actor=request.user, request=request)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def unblock(self, request, pk=None):
        usuario = UserAdminService.unblock(usuario=self.get_object(), actor=request.user, request=request)
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def roles(self, request, pk=None):
        serializer = RoleAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objetivo = self.get_object()
        _rechazar_si_es_uno_mismo(request.user, objetivo, 'cambiar los roles')
        _rechazar_si_el_objetivo_es_superusuario(request.user, objetivo, 'cambiar los roles')
        usuario = UserAdminService.assign_roles(
            usuario=objetivo, role_ids=serializer.validated_data['role_ids'], actor=request.user, request=request,
        )
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'], url_path='permissions')
    def permissions(self, request, pk=None):
        serializer = PermissionAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objetivo = self.get_object()
        _rechazar_si_es_uno_mismo(request.user, objetivo, 'cambiar los permisos')
        _rechazar_si_el_objetivo_es_superusuario(request.user, objetivo, 'cambiar los permisos')
        usuario = UserAdminService.assign_permissions(
            usuario=objetivo,
            codenames=_codenames_que_puede_otorgar(request.user, serializer.validated_data['codenames']),
            actor=request.user, request=request,
        )
        return Response(UserAdminDetailSerializer(usuario).data)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        objetivo = self.get_object()
        _rechazar_si_el_objetivo_es_superusuario(request.user, objetivo, 'restablecer la contraseña')
        usuario, password_temporal = UserAdminService.reset_password(usuario=objetivo, actor=request.user, request=request)
        return Response({**UserAdminDetailSerializer(usuario).data, 'temporary_password': password_temporal})

    @action(detail=True, methods=['post'])
    def superuser(self, request, pk=None):
        serializer = SuperuserAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = UserAdminService.set_superuser(
            usuario=self.get_object(), es_superusuario=serializer.validated_data['is_superuser'], actor=request.user, request=request,
        )
        return Response(UserAdminDetailSerializer(usuario).data)
