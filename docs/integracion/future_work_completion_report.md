# Informe final — trabajo futuro post-integración con skelleton_base

**Fecha de implementación**: 2026-07-31. **Rama**: `feature/post-integration-future-work`.

Este informe cierra los cuatro puntos que `docs/integracion/migration_report.md` documentaba
como "Trabajo futuro" tras la integración con `skelleton_base`: auditoría unificada (Módulo A),
integración visual con Bootstrap (Módulo B), landing pública profesional (Módulo C) y
recuperación de contraseña por correo (Módulo D).

## Estado inicial

- Dos sistemas de auditoría sin punto de consulta común: `apps.core.AuditLog` (seguridad/
  administración) y `cartera.DashboardAuditLog` (layout del editor visual).
- Colores institucionales (`SiteTheme`) alimentaban únicamente variables CSS propias del
  proyecto (`--color-*`); los componentes `react-bootstrap` (botones, badges, alertas, enlaces)
  seguían con la paleta por defecto de Bootstrap.
- `/` redirigía automáticamente a `/app/dashboards/cartera` (o al login); no existía ninguna
  página pública.
- No existía recuperación de contraseña sin sesión (solo cambio de contraseña autenticado,
  `/api/auth/password/change`).

## Análisis realizado

Se releyó `migration_report.md` para ubicar exactamente dónde se documentó cada pendiente, se
revisó la arquitectura resultante de la integración anterior (apps `core`/`permissions`/
`authentication`/`users`/`roles`/`branding`, `cartera`), y se verificó el estado de git (todo el
trabajo previo — paginación e integración con skelleton_base — seguía sin commitear en el árbol
de trabajo; no se realizó ninguna operación destructiva de Git). No se encontraron cambios locales
en conflicto con este trabajo.

## Arquitectura seleccionada (Módulo A)

Modelo `AuditEvent` (`backend/apps/audit/`) con 12 dominios (`SECURITY`, `AUTHENTICATION`,
`USER_MANAGEMENT`, `ROLE_MANAGEMENT`, `PERMISSION_MANAGEMENT`, `DASHBOARD_ACCESS`,
`DASHBOARD_LAYOUT`, `DASHBOARD_CONFIGURATION`, `DATA_SOURCE`, `EXPORT`, `FILE_UPLOAD`,
`SYSTEM_CONFIGURATION`), servicio único de escritura `apps.audit.services.log_event` (nunca
lanza excepción; sanitiza valores sensibles; captura actor/IP/user-agent/contexto). Detalle
completo: `docs/audit/unified_audit.md`.

## Auditorías encontradas

`apps.core.AuditLog` (12 filas en el entorno de desarrollo al momento de migrar: logins, altas de
usuario/rol, asignación de roles/permisos, cambio de branding) y `cartera.DashboardAuditLog` (0
filas en el entorno de desarrollo). Ambas tablas se conservan intactas (esquema y datos), como
archivo histórico de solo lectura — dejan de recibir filas nuevas.

## Estrategia de unificación

Todos los call-sites que escribían en `apps.core.AuditLog` (`apps/authentication/{services,
views}.py`, `apps/users/services.py`, `apps/roles/views.py`, `apps/branding/views.py`,
`apps/permissions/permissions.py`) y en `cartera.DashboardAuditLog`
(`cartera/services/dashboard_layout.py`) se migraron a `log_event(domain=..., ...)`.
`cartera/dashboard_views.py::DashboardVersionsView` pasó a consultar `AuditEvent` en vez de
`DashboardAuditLog`, con el mismo shape de respuesta que ya consumía el frontend.

## Datos migrados

Migración de datos no destructiva (`apps/audit/migrations/0002_migrar_historico_legacy.py`):
copia las 12 filas de `apps.core.AuditLog` a `AuditEvent` (0 de `DashboardAuditLog`, tabla vacía
en este entorno), con `metadata.source_audit_system` (`"core_auditlog_legacy"` /
`"dashboard_layout_legacy"`) y `metadata.legacy_id` apuntando a la fila de origen. Se preservan
fecha, usuario, acción, resultado y severidad (calculada, ya que las filas legacy no tenían este
campo). Reversible sin tocar las tablas legacy (el rollback solo borra los `AuditEvent` que la
propia migración creó).

## Cambios de Bootstrap (Módulo B)

`SiteTheme` ganó 5 campos (`color_success`, `color_danger`, `color_warning`, `color_info`,
`color_button_text`). Se descubrió que el `bootstrap.min.css` precompilado que usa el proyecto no
lee `--bs-primary` (u otras variables de ese estilo) dentro de `.btn-primary`/`.btn-outline-*`/
`.alert-*`: esas clases fijan sus propias variables internas con el hexadecimal ya resuelto por
Sass en tiempo de build. La solución fue inyectar en tiempo de ejecución una hoja de estilos
(`<style id="theme-bootstrap-overrides">`) que redefine esas variables internas sobre las clases
reales que usa la aplicación (`.btn-*`, `.btn-outline-*`, `.bg-*`, `.text-*`, `.alert-*`, enlaces,
foco de formularios, casillas marcadas). Aviso de contraste WCAG AA no bloqueante en
`/admin/settings`, comparando cada color contra su contraparte real de uso (no contra negro/blanco
absolutos, que matemáticamente siempre pasan contra al menos uno de los dos). Detalle completo,
incluidos los dos hallazgos de este módulo: `docs/frontend/bootstrap_theme.md`.

## Secciones de la landing (Módulo C)

`/` renderiza ahora una landing pública (`frontend/src/pages/public/LandingPage.jsx`), sin
autenticación: Inicio (hero con mockup de dashboard en CSS/HTML puro) → Plataforma (9
capacidades) → Dashboards (10 áreas de ejemplo — Gerencia, Finanzas, Operaciones, Logística,
Comercial, Cobranzas, Talento Humano, Tecnología, Servicio al Cliente, Proyectos — con ícono,
indicadores de ejemplo y etiqueta "Acceso restringido"; ninguna es un enlace real) →
Funcionamiento (diagrama de flujo: Fuentes empresariales → Vistas autorizadas → Procesamiento →
Roles y permisos → Dashboard) → Seguridad (7 puntos) → Beneficios (10 puntos) → CTA → pie de
página (nombre/logo institucional, descripción, enlaces, año dinámico). Contenido separado del
componente (`frontend/src/config/landingContent.js`), config-driven sin ser un editor visual
completo (explícitamente no requerido en esta fase). Menú sticky con resaltado de sección activa,
scroll suave y hamburguesa móvil. Dos bugs de CSS encontrados y corregidos durante la
verificación manual (el navbar sticky tapaba el título de la sección de destino; una regla
`overflow-x: hidden` rompía el propio `position: sticky`) — detalle en
`docs/public/landing_page.md`.

## Flujo de recuperación (Módulo D)

`PasswordResetToken` (hash SHA-256 del token, nunca el valor crudo), servicio
`PasswordResetService` (`solicitar`/`validar`/`confirmar`), 3 endpoints
(`POST /api/auth/password-reset/{request,validate,confirm}`) con los contratos de request/
response exactos especificados. Mensaje de respuesta de `solicitar` siempre genérico (nunca
revela si el correo existe). Token de un solo uso, expiración configurable (30 min por defecto),
se invalida cualquier token anterior sin usar al emitir uno nuevo, se revocan todas las sesiones
activas del usuario al completar el cambio. Rate limiting con `ScopedRateThrottle` (5/hora por
IP). 6 acciones de auditoría (`PASSWORD_RESET_REQUESTED/EMAIL_SENT/EMAIL_FAILED/TOKEN_INVALID/
TOKEN_EXPIRED/COMPLETED`), dominio `AUTHENTICATION`. Frontend:
`pages/authentication/{ForgotPasswordPage,ResetPasswordPage}.jsx`, rutas públicas
`/forgot-password` y `/reset-password`, enlace "¿Olvidaste tu contraseña?" en `LoginPage.jsx`.
Detalle completo: `docs/authentication/password_recovery.md`.

## Configuración de correo

Variables nuevas en `.env`/`.env.example`: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`,
`DEFAULT_FROM_EMAIL`, `FRONTEND_URL`, `PASSWORD_RESET_TOKEN_LIFETIME_MINUTES`,
`PASSWORD_RESET_THROTTLE_RATE`. Por defecto, backend de consola (nunca envía correo real). Para
la prueba controlada de la siguiente sección, el usuario proporcionó credenciales SMTP reales
(Gmail) directamente en el chat, que se escribieron únicamente en `backend/.env` (gitignorado,
nunca commiteado). Tras validar el envío, `EMAIL_BACKEND` se devolvió a consola para evitar
envíos reales accidentales en pruebas manuales futuras; las credenciales quedaron guardadas en
`.env` por si se necesita repetir la prueba deliberadamente.

## Resultado del correo QA

Ejecutado con `python manage.py test_password_reset_email --email dpenarreta@grupolaar.com --yes`,
reutilizando el mismo `PasswordResetService.solicitar(...)` que usa el endpoint público (no hay
lógica duplicada ni el correo de prueba hardcodeado en el camino de producción).

- **Destinatario**: dpenarreta@grupolaar.com
- **Fecha y hora**: 2026-07-31, 13:31:51 UTC (08:31:51 hora de Guayaquil)
- **Resultado**: enviado correctamente (`PASSWORD_RESET_EMAIL_SENT`, `result=SUCCESS`)
- **ID del evento de auditoría**: 37
- **Proveedor/backend utilizado**: SMTP real (`smtp.gmail.com:587`, TLS) vía
  `django.core.mail.backends.smtp.EmailBackend`

Un único envío, tal como exige el prompt — no se ejecutó el comando más de una vez con este
destinatario.

## Archivos creados

Backend: `apps/audit/{models,services,filters,serializers,views,urls,admin,apps,tests}.py` +
`migrations/{0001_initial,0002_migrar_historico_legacy}.py`; `apps/branding/migrations/
0003_agregar_colores_bootstrap.py`; `apps/authentication/models.py` (modelo
`PasswordResetToken`, agregado al archivo existente) + `migrations/0003_passwordresettoken.py`;
`apps/authentication/templates/authentication/password_reset_email.{html,txt}`;
`apps/authentication/management/{__init__,commands/__init__,commands/
test_password_reset_email}.py`. Frontend: `services/auditService.js`,
`pages/administration/audit/AuditListPage.jsx`, `utils/colorContrast.js`,
`config/landingContent.js`, `components/public/PublicNavbar.jsx`,
`pages/public/LandingPage.jsx`, `styles/landing.css`,
`pages/authentication/{ForgotPasswordPage,ResetPasswordPage}.jsx`; tests:
`AuditListPage,ThemeContext(actualizado),SettingsPage(actualizado),colorContrast,
landingContent,PublicNavbar,LandingPage,ForgotPasswordPage,ResetPasswordPage`.test.{jsx,js}.
Documentación: `docs/audit/unified_audit.md`, `docs/frontend/bootstrap_theme.md`,
`docs/public/landing_page.md`, `docs/authentication/password_recovery.md`,
`docs/integracion/future_work_completion_report.md` (este archivo). Gherkin:
`tests/qa/post_integration_future_work.feature` (16 escenarios).

## Archivos modificados

Backend: `apps/core/audit.py` (se retira `record_audit_event`), `apps/core/tests.py`,
`apps/authentication/{services,views,serializers,urls,tests}.py`, `apps/users/services.py`,
`apps/roles/{views,tests}.py`, `apps/branding/{models,catalog,serializers}.py`,
`apps/permissions/permissions.py`, `cartera/services/dashboard_layout.py`,
`cartera/dashboard_views.py`, `cartera/tests/test_dashboard_layout.py`, `config/{settings,
urls}.py`, `.env`/`.env.example`. Frontend: `context/ThemeContext.jsx`,
`pages/administration/settings/SettingsPage.jsx`, `config/adminMenu.js`, `routes/AppRoutes.jsx`,
`pages/authentication/LoginPage.jsx`, `services/authService.js`, `tests/setup.js`. Documentación:
`README.md`, `docs/integracion/migration_report.md`, `docs/integracion/
post_integration_validation.md`.

## Migraciones

`audit.0001_initial` (crea `AuditEvent`), `audit.0002_migrar_historico_legacy` (datos, no
destructiva, reversible), `branding.0002_seed_default_theme` (corregida: ahora filtra
`DEFAULT_THEME` a los campos del modelo histórico, para tolerar campos agregados en migraciones
posteriores), `branding.0003_agregar_colores_bootstrap` (esquema), `authentication.
0003_passwordresettoken` (crea `PasswordResetToken`). Todas aplicadas y verificadas en el entorno
de desarrollo; `manage.py makemigrations --check` sin cambios pendientes.

## Pruebas ejecutadas

`manage.py test` (backend, SQL Server real) y `npm run test`/`vitest run` (frontend) tras cada
módulo y en el cierre.

## Pruebas aprobadas

**173 pruebas backend**, **207 pruebas frontend** — todas en verde al cierre de los cuatro
módulos.

## Pruebas fallidas

Ninguna al cierre. Durante el desarrollo se encontraron y corrigieron en el momento: migración de
seed de `branding` rota por campos nuevos (ver "Migraciones"), severidad no calculada en la
migración de datos históricos, prueba de rate limiting con estado de caché compartido entre
pruebas, contenido de la landing no alineado con la especificación exacta del prompt (corregido
tras releer la sección 6 completa), y dos bugs de CSS en el navbar sticky de la landing (ver
"Secciones de la landing"). Ninguno quedó sin resolver.

## Riesgos pendientes

- No se verificó la landing, el editor visual ni el panel de administración en un dispositivo
  móvil real (solo revisión de CSS responsivo y captura de pantalla en Chrome de escritorio).
- El correo de recuperación no se probó contra un proveedor SMTP distinto de Gmail; el mecanismo
  (`EmailMultiAlternatives` + variables de entorno estándar de Django) es compatible con cualquier
  servidor SMTP, pero no se validó con otro.
- `EMAIL_BACKEND` quedó en consola tras la prueba real — si se necesita un segundo envío de
  validación, hay que cambiarlo de vuelta a `django.core.mail.backends.smtp.EmailBackend`
  manualmente en `.env`.

## Evidencias

Verificación manual en Chrome (capturas de pantalla revisadas durante la sesión, no adjuntas a
este documento): listado y detalle de auditoría con datos migrados reales; cambio de color
institucional reflejado en botones/badges/alertas reales; landing completa navegada por scroll
con el menú pegado correctamente; flujo de recuperación de contraseña de extremo a extremo con un
usuario desechable (creado y eliminado durante la verificación) — solicitud, token real capturado
del backend de consola, restablecimiento, login con la contraseña nueva, y rechazo de la
reutilización del mismo enlace. Sin errores de consola del navegador en ninguna verificación.
