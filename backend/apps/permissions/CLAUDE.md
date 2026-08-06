# Módulo: permissions

Hereda `../../CLAUDE.md` y `@.claude/rules/security.md`.

## Responsabilidad

Catálogo cerrado de permisos — única fuente de verdad de qué acciones existen en el sistema. No
gestiona roles (`apps.roles`) ni usuarios (`apps.users`), solo el catálogo y su resolución.

## Estructura

- `catalog.py` — `PERMISSION_CATALOG`: lista de `{module, codename, name}`. Formato de codename:
  `modulo.accion` (ej. `usuarios.ver`, `dashboard.layout.edit`). Incluye los 10 permisos
  `dashboard.*` que ya usaba `cartera/permisos.py` **sin renombrarlos** — no cambies un codename
  `dashboard.*` sin actualizar `cartera/permisos.py` a la vez, son el mismo string en dos lugares.
- `authorization.py` — `user_has_permission(user, codename)`: `True` siempre si
  `user.is_superuser`; si no, `user.has_perm(f'permissions.{codename}')`.
  `get_user_permission_codenames(user)`: para superusuario retorna el catálogo completo.
- `permissions.py` — `require_permission(codename)` (fábrica de `BasePermission` DRF, audita
  `ACCESS_DENIED` al denegar) e `IsSuperuser` (exige `is_superuser=True` puro, sin pasar por el
  catálogo).

## Reglas

- IMPORTANT: agregar un permiso nuevo es agregar una entrada a `PERMISSION_CATALOG` — no crees un
  segundo catálogo ni una tabla de permisos paralela. Un permiso nuevo queda disponible
  automáticamente para asignar a cualquier rol.
- `require_permission('modulo.accion')` es para permisos de negocio asignables a un rol.
  `IsSuperuser` es para acciones que ni un permiso de negocio debe poder otorgar (ej. marcar a
  otro usuario como superusuario) — no la uses como sinónimo de "requiere más privilegios".
- Los codenames reales de `Permission` en base de datos están bajo
  `content_type__app_label='permissions'` — al filtrar `Permission.objects.filter(codename=...)`
  desde otra app, incluye siempre ese filtro de `content_type` o corres el riesgo de matchear un
  permiso automático de Django del modelo equivocado.

## Evita

- No calcules "¿tiene acceso?" comparando el nombre de un grupo/rol — siempre contra el codename
  resuelto por `user_has_permission`/`user.permissions` (frontend).
