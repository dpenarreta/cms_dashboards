# Recuperación de contraseña por correo (Módulo D)

Parte de "Trabajo futuro post-integración con skelleton_base" (ver
`docs/integracion/migration_report.md`, sección "Trabajo futuro completado").

## Diseño

### Token (`apps/authentication/models.py::PasswordResetToken`)

`id` (UUID), `user` (FK, `CASCADE`), `token_hash` (SHA-256 del token crudo, único, indexado),
`expires_at`, `used_at` (nulo hasta que se consume). El valor crudo del token
(`secrets.token_urlsafe(32)`, 256 bits de entropía) **nunca se persiste** — solo su hash. Vida
configurable por `PASSWORD_RESET_TOKEN_LIFETIME_MINUTES` (default 30 minutos). Al solicitar un
nuevo token, cualquier token anterior sin usar del mismo usuario se invalida
(`used_at = now()`), para que solo exista un enlace válido a la vez.

### Servicio (`apps/authentication/services.py::PasswordResetService`)

- `solicitar(email)` — busca el usuario por correo (case-insensitive). **Siempre** devuelve el
  mismo mensaje genérico (`"Si el correo está registrado, recibirás un enlace para restablecer tu
  contraseña."`), exista o no el correo, esté activo o no, y aunque el envío del correo falle
  internamente (excepción capturada, nunca se propaga al llamador) — así se evita por completo la
  enumeración de usuarios. Registra `PASSWORD_RESET_REQUESTED` siempre; `PASSWORD_RESET_EMAIL_SENT`
  o `PASSWORD_RESET_EMAIL_FAILED` solo si el usuario existe y está activo.
- `validar(raw_token)` — resuelve por hash, verifica que no esté usado ni expirado. Registra
  `PASSWORD_RESET_TOKEN_INVALID`/`PASSWORD_RESET_TOKEN_EXPIRED` cuando corresponde. No consume el
  token (permite que la pantalla de restablecimiento verifique antes de mostrar el formulario).
- `confirmar(raw_token, new_password)` — reutiliza `validar(...)`, cambia la contraseña
  (`set_password`, hash Argon2 vía `PASSWORD_HASHERS`), marca el token usado, **revoca todas las
  sesiones activas del usuario** (`SessionService.revocar_todas`, ya existía para
  `logout-all`/cambio de contraseña propio — se reutiliza, no se duplica), registra
  `PASSWORD_RESET_COMPLETED`.

Todos los eventos van al dominio `AUTHENTICATION` del sistema de auditoría unificado (Módulo A) —
ningún dato sensible se guarda en `metadata`/`previous_values`/`new_values` (nunca la contraseña,
nunca el token crudo, nunca el hash completo en un campo de texto libre distinto de
`token_hash`).

### API

| Endpoint | Body | Respuesta |
|---|---|---|
| `POST /api/auth/password-reset/request` | `{"email": "..."}` | `{"message": "..."}` (siempre genérico, 200) |
| `POST /api/auth/password-reset/validate` | `{"token": "..."}` | `{"valid": true}` (200) o error 400 (`TOKEN_INVALIDO`/`TOKEN_EXPIRADO`) |
| `POST /api/auth/password-reset/confirm` | `{"token", "new_password", "confirm_password"}` | `{"message": "..."}` (200) o error 400 |

`request` está protegido con `ScopedRateThrottle` (`password_reset`, configurable vía
`PASSWORD_RESET_THROTTLE_RATE`, default `5/hour` por IP) — previene abuso de envío masivo sin
tabla ni infraestructura nueva (mecanismo nativo de DRF).

### Correo

`EmailMultiAlternatives` (texto + HTML), plantillas en
`apps/authentication/templates/authentication/password_reset_email.{html,txt}`. Asunto exacto:
"Recuperación de contraseña | CMS Dashboards". El enlace se arma siempre desde
`settings.FRONTEND_URL` (nunca un dominio hardcodeado) + `/reset-password?token={token}`. Incluye
nombre del usuario (si está disponible), tiempo de expiración, aviso de "si no fuiste tú, ignora
este mensaje", e identidad institucional (nombre y color primario desde `SiteTheme.get_solo()`).

Variables de entorno nuevas (`.env.example`): `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL`,
`FRONTEND_URL`, `PASSWORD_RESET_TOKEN_LIFETIME_MINUTES`, `PASSWORD_RESET_THROTTLE_RATE`. Por
defecto, `EMAIL_BACKEND` apunta al backend de consola de Django — **nunca se envía un correo real
sin configurar explícitamente un servidor SMTP** en `.env` (que está gitignorado).

### Frontend

`pages/authentication/{ForgotPasswordPage,ResetPasswordPage}.jsx`, rutas públicas
`/forgot-password` y `/reset-password` (fuera de `AuthenticatedLayout`, sin `RequirePermission`).
Enlace "¿Olvidaste tu contraseña?" en `LoginPage.jsx`. `ResetPasswordPage` valida el token al
montar (antes de mostrar el formulario) para no dejar al usuario escribir una contraseña nueva
sobre un enlace ya inválido; usa `is-invalid`/`text-danger`/`alert-danger` y
`alert-success` de Bootstrap (sección 12 del prompt), no clases propias.

### Comando QA (`apps/authentication/management/commands/test_password_reset_email.py`)

`python manage.py test_password_reset_email --email <correo>` — reutiliza
`PasswordResetService.solicitar(...)` (el mismo camino de producción, no lógica duplicada), pide
confirmación interactiva salvo `--yes`, nunca imprime el token completo (el propio comando no lo
expone — si `EMAIL_BACKEND` es el de consola, Django vuelca el correo completo por su cuenta, algo
del backend elegido, no del comando), verifica el resultado real consultando el `AuditEvent`
(`PASSWORD_RESET_EMAIL_SENT`/`PASSWORD_RESET_EMAIL_FAILED`) que la propia llamada acaba de
registrar, y retorna código de salida distinto de 0 si el envío falló. El correo de prueba
(`dpenarreta@grupolaar.com`) **no está hardcodeado en ningún lugar de la lógica productiva** —
solo se usa como argumento `--email` al ejecutar el comando manualmente.

## Verificación

- Backend: `apps/authentication/tests.py` (`PasswordResetServiceTests`,
  `PasswordResetApiTests`) — 17 pruebas: solicitud válida, correo no registrado, mensaje genérico,
  usuario inactivo, enlace con `FRONTEND_URL`, invalidación del token anterior, token
  válido/inexistente/expirado/ya usado, contraseñas no coincidentes, contraseña débil, cambio
  exitoso (incluye login con la contraseña nueva), revocación de sesiones, rate limiting. Todas
  usan el backend de correo en memoria de Django (automático durante `TestCase`, sin
  configuración) — **nunca se envía un correo real en la suite automatizada**.
- Frontend: `ForgotPasswordPage.test.jsx`, `ResetPasswordPage.test.jsx`, prueba agregada a
  `LoginPage.test.jsx` para el enlace nuevo.
- Verificación manual en Chrome: se creó un usuario desechable (`qa_reset_test`, eliminado al
  terminar), se solicitó la recuperación desde `/forgot-password`, se tomó el enlace real impreso
  por el backend de consola, se completó el restablecimiento en `/reset-password`, se confirmó
  por consulta directa a la base de datos que la contraseña nueva funciona y que se registró
  `PASSWORD_RESET_COMPLETED`, y se verificó que reutilizar el mismo enlace después es rechazado
  ("Este enlace de recuperación no es válido o ya expiró.").
- La prueba de envío **real** a `dpenarreta@grupolaar.com` (sección 9 del prompt) se documenta por
  separado, una vez configurado el SMTP real — ver
  `docs/integracion/future_work_completion_report.md`.
