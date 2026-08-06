# Módulo: roles

Hereda `../../CLAUDE.md`.

## Responsabilidad

CRUD de roles. No define modelo propio: un "rol" **es** un `django.contrib.auth.models.Group`
(decisión 3, `docs/integracion/decisions.md`) — este módulo no tiene `models.py`.

## Estructura

- `views.py` — `RoleViewSet` sobre `Group`. Action custom `permissions-catalog` (`GET
  /api/roles/permissions-catalog/`) devuelve el catálogo agrupado por módulo.
- `serializers.py` — `RoleWriteSerializer.validate_name` rechaza nombres duplicados
  (case-insensitive). `validate_permission_codenames` rechaza cualquier codename fuera de
  `apps.permissions.catalog.PERMISSION_CATALOG` → 400.
- Los "permisos de un rol" son `Permission` filtrados por `content_type__app_label='permissions'`
  — no todos los `Permission` que Django genera automáticamente por modelo.

## Relación usuario-rol

Un usuario pertenece a roles vía `user.groups` (M2M nativo de Django). El rol
`ADMINISTRADOR_GENERAL` se siembra con el catálogo completo de permisos
(`apps/roles/migrations/0001_initial.py`) — el acceso de administrador **no** depende de que el
rol se llame así, depende de qué permisos tiene asignados; no compares por nombre de rol en
código nuevo.

## Evita

- IMPORTANT: `RoleViewSet.perform_destroy` borra cualquier rol sin ninguna protección, incluido
  `ADMINISTRADOR_GENERAL` — si el último rol/usuario con `usuarios.crear`/`roles.editar` se
  borra, el sistema puede quedar sin forma de administrarse desde la UI. Si tocas
  `perform_destroy`, considera agregar el mismo tipo de guard que ya existe en `apps.users`
  (`_es_ultimo_administrador_activo`) antes de asumir que borrar roles es siempre seguro.

## Pruebas mínimas al tocar este módulo

Rechazo de permiso no reconocido (400), rechazo de nombre duplicado (400), 403 sin `roles.ver`/
`roles.editar`, auditoría en creación/edición (`ROLE_MANAGEMENT`).
