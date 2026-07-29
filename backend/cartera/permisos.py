"""Permisos del editor visual de dashboards (sección 6 del prompt de personalización).

La aplicación no tiene sistema de autenticación (decisión documentada en el README). Por eso
`permisos_del_usuario` es hoy un único punto que concede todos los permisos sin verificar nada
— pero es el ÚNICO lugar que las vistas consultan, así que conectar un sistema de usuarios/roles
real en el futuro es cambiar esta función, no la lógica de cada endpoint.
"""

DASHBOARD_VIEW = 'dashboard.view'
DASHBOARD_EDIT = 'dashboard.edit'
DASHBOARD_LAYOUT_EDIT = 'dashboard.layout.edit'
DASHBOARD_COMPONENT_STYLE = 'dashboard.component.style'
DASHBOARD_COMPONENT_CREATE = 'dashboard.component.create'
DASHBOARD_COMPONENT_DELETE = 'dashboard.component.delete'
DASHBOARD_CONFIGURATION_RESET = 'dashboard.configuration.reset'

TODOS_LOS_PERMISOS = [
    DASHBOARD_VIEW,
    DASHBOARD_EDIT,
    DASHBOARD_LAYOUT_EDIT,
    DASHBOARD_COMPONENT_STYLE,
    DASHBOARD_COMPONENT_CREATE,
    DASHBOARD_COMPONENT_DELETE,
    DASHBOARD_CONFIGURATION_RESET,
]


def permisos_del_usuario(request):
    """Sin autenticación implementada: concede todos los permisos a cualquier solicitud.

    Devuelve un dict {permiso: bool} para que el código llamador siga preguntando por permiso
    específico (`permisos_del_usuario(request)[DASHBOARD_EDIT]`) en vez de asumir un booleano
    global, de modo que otorgar permisos de forma diferenciada después no requiera tocar a los
    llamadores.
    """
    return {permiso: True for permiso in TODOS_LOS_PERMISOS}


def tiene_permiso(request, permiso):
    return permisos_del_usuario(request).get(permiso, False)
