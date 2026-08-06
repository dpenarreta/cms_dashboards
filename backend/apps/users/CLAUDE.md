# Módulo: users

Hereda `../../CLAUDE.md` y `@.claude/rules/security.md`.

## Responsabilidad

Fuente única de usuarios (`AUTH_USER_MODEL = 'users.User'`, `AbstractUser` extendido). CRUD
administrativo, estado (activo/deshabilitado/bloqueado), asignación de roles y permisos directos,
reset de contraseña por admin. No pertenece aquí: login/sesiones (`apps.authentication`) ni el
catálogo de permisos en sí (`apps.permissions`).

## Estructura

- `models.py` — `User(AbstractUser, BaseModel)`: `status` (choices ACTIVE/DISABLED/BLOCKED,
  `save()` sincroniza `is_active` automáticamente), `must_change_password`, `created_by`/
  `updated_by` (self-FK).
- `services.py` — `UserAdminService` (todos `@staticmethod`, firma `(*, usuario, ..., actor=None)`,
  todos auditan con `log_event(domain=AuditEvent.Domain.USER_MANAGEMENT, ...)`).
- `views.py` — `UserAdminViewSet`, `http_method_names` sin `delete` (no hay borrado de usuarios,
  solo deshabilitar/bloquear). `ACTION_PERMISSION_CLASSES` mapea cada `@action` a su codename.

## Reglas

- IMPORTANT: nunca se puede deshabilitar, bloquear ni quitar superusuario al **último**
  administrador general activo (`_es_ultimo_administrador_activo`) — cualquier acción nueva que
  cambie `status`/`is_superuser` debe pasar por ese guard o uno equivalente.
- Cambiar `usuario.password` directo está prohibido — siempre `usuario.set_password(...)`.
- `set_superuser` solo la invoca `IsSuperuser` (no `require_permission`) — otorgar superusuario no
  debe depender de un permiso de negocio asignable, ver `@.claude/rules/security.md`.
- Un reset de contraseña por admin genera una temporal aleatoria (nunca la elige el admin a mano),
  fuerza `must_change_password=True` y revoca sesiones activas — la contraseña en claro solo
  existe en el valor de retorno de `reset_password`, nunca se persiste ni se loguea.

## Evita

- No asumas que `is_superuser=True` implica que el frontend deba mostrar controles distintos a
  los que ya decide `user.permissions` — el catálogo completo ya llega ahí.
- No agregues un endpoint `DELETE` para usuarios — el modelo de negocio es deshabilitar/bloquear,
  nunca borrar (histórico de auditoría/`created_by`/`updated_by` depende de que el usuario exista).
