"""Resolución de autorización sobre el catálogo cerrado de `apps.permissions.catalog`.

Los permisos de Django se identifican internamente como `"<app_label>.<codename>"`. Como el
modelo ancla `ModulePermission` vive en la app `permissions`, el identificador interno real de
cada permiso es `"permissions.<codename>"` (ej. `"permissions.usuarios.ver"`), aunque el
`codename` "de negocio" que se expone en la API y que usa `cartera.permisos` es solo
`"usuarios.ver"`. Esta función es el único lugar que conoce ese detalle.
"""

_APP_LABEL = 'permissions'


def _permiso_django(codename):
    return f'{_APP_LABEL}.{codename}'


def get_user_permission_codenames(user):
    """Codenames de negocio (sin el prefijo interno de Django) efectivos del usuario."""
    if not user or not user.is_authenticated:
        return set()
    from .catalog import PERMISSION_CATALOG
    if user.is_superuser:
        return {p['codename'] for p in PERMISSION_CATALOG}
    prefijo = f'{_APP_LABEL}.'
    return {
        permiso[len(prefijo):]
        for permiso in user.get_all_permissions()
        if permiso.startswith(prefijo)
    }


def user_has_permission(user, codename):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.has_perm(_permiso_django(codename))
