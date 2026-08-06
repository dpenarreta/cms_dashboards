from rest_framework.permissions import BasePermission

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.core.audit import request_meta

from .authorization import user_has_permission


class HasModulePermission(BasePermission):
    """Exige un permiso concreto del catálogo. Uso: `permission_classes = [HasModulePermission]`
    junto a un atributo `required_permission = 'usuarios.ver'` en la vista, o subclasificar y
    fijar `required_permission` como atributo de clase (ver `HasModulePermissionFactory`)."""

    required_permission = None

    def has_permission(self, request, view):
        permiso = getattr(view, 'required_permission', None) or self.required_permission
        if not permiso:
            return True
        concedido = user_has_permission(request.user, permiso)
        if not concedido and request.user and request.user.is_authenticated:
            ip, user_agent = request_meta(request)
            log_event(
                domain=AuditEvent.Domain.SECURITY, action='ACCESS_DENIED', result=AuditEvent.Result.DENIED,
                actor=request.user, entity_type='endpoint', entity_id=request.path,
                metadata={'required_permission': permiso, 'method': request.method},
                ip_address=ip, user_agent=user_agent,
            )
        return concedido


def require_permission(codename):
    """Fábrica: `permission_classes = [require_permission('usuarios.ver')]`."""
    return type(f'Require_{codename.replace(".", "_")}', (HasModulePermission,), {'required_permission': codename})


class IsSuperuser(BasePermission):
    """Exige que el usuario autenticado sea superusuario de Django (`is_superuser=True`) — para
    acciones que ni siquiera un permiso del catálogo de negocio debe poder otorgar (conceder
    superusuario a otra cuenta). Un permiso de catálogo no sirve acá porque `is_superuser=True`
    bypassa por completo ese catálogo (`authorization.user_has_permission`); si `usuarios.editar`
    alcanzara para esta acción, cualquiera con ese permiso podría fabricarse un superusuario
    nuevo y escalar sus propios privilegios más allá de lo que se le otorgó."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
