"""Permisos del editor visual de dashboards (sección 6 del prompt de personalización).

Desde la Fase 5 de la integración con skelleton_base (docs/integracion/decisions.md #6),
`permisos_del_usuario` resuelve siempre permisos reales contra `request.user` — se retiró el
fallback histórico que concedía todo sin autenticación, ahora que el dashboard exige
`IsAuthenticated` (`REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES`) y el frontend ya tiene pantalla de
login. Sin usuario autenticado, todos los permisos son `False` (fallo cerrado, no abierto).
"""

from apps.permissions.authorization import user_has_permission

from .models import Dashboard

DASHBOARD_CREAR = 'dashboard.crear'
DASHBOARD_EDITAR = 'dashboard.editar'
DASHBOARD_ELIMINAR = 'dashboard.eliminar'
DASHBOARD_VIEW = 'dashboard.view'
DASHBOARD_EDIT = 'dashboard.edit'
DASHBOARD_LAYOUT_EDIT = 'dashboard.layout.edit'
DASHBOARD_COMPONENT_STYLE = 'dashboard.component.style'
DASHBOARD_COMPONENT_CREATE = 'dashboard.component.create'
DASHBOARD_COMPONENT_DELETE = 'dashboard.component.delete'
DASHBOARD_CONFIGURATION_RESET = 'dashboard.configuration.reset'

TODOS_LOS_PERMISOS = [
    DASHBOARD_CREAR,
    DASHBOARD_EDITAR,
    DASHBOARD_ELIMINAR,
    DASHBOARD_VIEW,
    DASHBOARD_EDIT,
    DASHBOARD_LAYOUT_EDIT,
    DASHBOARD_COMPONENT_STYLE,
    DASHBOARD_COMPONENT_CREATE,
    DASHBOARD_COMPONENT_DELETE,
    DASHBOARD_CONFIGURATION_RESET,
]


def permisos_del_usuario(request):
    """Devuelve un dict {permiso: bool} para que el código llamador siga preguntando por permiso
    específico (`permisos_del_usuario(request)[DASHBOARD_EDIT]`) en vez de asumir un booleano
    global. Se resuelve siempre contra `request.user` (ver docstring del módulo).
    """
    usuario = getattr(request, 'user', None)
    return {permiso: user_has_permission(usuario, permiso) for permiso in TODOS_LOS_PERMISOS}


def tiene_permiso(request, permiso):
    return permisos_del_usuario(request).get(permiso, False)


def _dashboard_o_none(dashboard_id):
    try:
        return Dashboard.objects.get(dashboard_id=dashboard_id)
    except Dashboard.DoesNotExist:
        return None


def _acl_configurada(dashboard):
    return dashboard.roles_editores.exists() or dashboard.roles_lectores.exists()


def _es_dueno_o_superusuario(request, dashboard):
    usuario = getattr(request, 'user', None)
    if not usuario or not usuario.is_authenticated:
        return False
    return bool(usuario.is_superuser or (dashboard.owner_id and dashboard.owner_id == usuario.id))


def tiene_acceso_dashboard(request, dashboard_id, *, permiso_global, requiere_edicion=False):
    """Punto único de autorización por dashboard (control de acceso por roles editores/lectores +
    dueño). Si el dashboard no existe o no tiene ACL propia configurada (sin roles asignados a
    ninguno de los 2 grupos — el caso de todo dashboard hoy y por defecto), se comporta exactamente
    igual que siempre: `tiene_permiso(request, permiso_global)`. En cuanto se le asignan roles a
    cualquiera de los 2 grupos, ese dashboard queda restringido a su dueño, al superusuario, o a
    quien tenga uno de esos roles — `roles_editores` alcanza para ver Y editar; `roles_lectores`
    solo para ver."""
    dashboard = _dashboard_o_none(dashboard_id)
    if dashboard is None or not _acl_configurada(dashboard):
        return tiene_permiso(request, permiso_global)

    if _es_dueno_o_superusuario(request, dashboard):
        return True

    usuario = getattr(request, 'user', None)
    if not usuario or not usuario.is_authenticated:
        return False

    grupos_permitidos = dashboard.roles_editores.all()
    if not requiere_edicion:
        grupos_permitidos = grupos_permitidos | dashboard.roles_lectores.all()
    return usuario.groups.filter(pk__in=grupos_permitidos.values('pk')).exists()


def puede_administrar_acceso(request, dashboard_id):
    """Editar la configuración de acceso de un dashboard (sus 2 grupos de roles) o reasignar su
    dueño está reservado al dueño actual o al superusuario — a propósito no cae a ningún permiso
    global del catálogo, ni siquiera `dashboard.editar`."""
    dashboard = _dashboard_o_none(dashboard_id)
    if dashboard is None:
        return False
    return _es_dueno_o_superusuario(request, dashboard)
