"""Permisos del editor visual de dashboards (sección 6 del prompt de personalización).

Desde la Fase 5 de la integración con skelleton_base (docs/integracion/decisions.md #6),
`permisos_del_usuario` resuelve siempre permisos reales contra `request.user` — se retiró el
fallback histórico que concedía todo sin autenticación, ahora que el dashboard exige
`IsAuthenticated` (`REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES`) y el frontend ya tiene pantalla de
login. Sin usuario autenticado, todos los permisos son `False` (fallo cerrado, no abierto).
"""

from apps.permissions.authorization import user_has_permission

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
