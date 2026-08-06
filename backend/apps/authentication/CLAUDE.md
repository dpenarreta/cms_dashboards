# Módulo: authentication

Hereda `../../CLAUDE.md` y `@.claude/rules/security.md` (hash, revocación de sesión, fuerza
bruta). Esto cubre solo lo específico de este módulo.

## Responsabilidad

Login/logout/logout-all/refresh/me, cambio de contraseña propia, recuperación por correo
(solicitud/validación/confirmación). No pertenece aquí: gestión administrativa de OTROS usuarios
(eso es `apps.users`) ni el catálogo de permisos (`apps.permissions`).

## Estructura

- `models.py` — `Session` (revocación propia, claim `sid`), `LoginAttempt` (fuerza bruta),
  `PasswordResetToken` (hash del token, nunca el token en claro).
- `services.py` — `BruteForceProtectionService`, `SessionService`, `AuthenticationService`,
  `PasswordResetService`. Toda la lógica de negocio vive acá, no en `views.py`.

## Contrato del usuario autenticado

`GET /api/auth/me` expone `{ ..., permissions: [...] }` — `permissions` ya trae el catálogo
completo resuelto para un superusuario (`apps.permissions.authorization.get_user_permission_codenames`).
El frontend nunca debe verificar `is_superuser` por separado para decidir acceso a una función de
negocio; compara siempre contra `permissions`.

## Reglas

- IMPORTANT: nunca hardcodees el dominio del enlace de recuperación de contraseña — siempre desde
  `settings.FRONTEND_URL` (`.env`, nunca literal en código).
- La respuesta de `POST /api/auth/password-reset/request` es **siempre** el mismo mensaje
  genérico, exista o no el correo — nunca reveles si un email está registrado. Al comparar
  contraseña cuando el usuario no existe, igual se ejecuta un hash señuelo
  (`_DUMMY_PASSWORD_HASH`) para no delatar la diferencia por tiempo de respuesta.
- `Session.revocar_todas(usuario)` se llama en: deshabilitar/bloquear usuario, reset de contraseña
  (propio o por admin), confirmación de recuperación por correo. Si agregas una acción que cambia
  credenciales o desactiva una cuenta, replica esta llamada.
- No actives `rest_framework_simplejwt.token_blacklist` — la revocación es vía `Session`, no vía
  blacklist nativa (decisión 8, `docs/integracion/decisions.md`).

## Pruebas mínimas al tocar este módulo

Login con credenciales inválidas no revela si el usuario existe; bloqueo tras
`LOGIN_MAX_FAILED_ATTEMPTS`; token de recuperación expirado/usado se rechaza; revocación de
sesiones tras cambio de contraseña.
