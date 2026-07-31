# Matriz de migración de archivos — skelleton_base → cms_dashboards

Todas las rutas de origen son relativas a `C:\Users\itinnouio\ProyectosClaude\skelleton_base\`.
Todas las rutas de destino son relativas a `C:\Users\itinnouio\ProyectosClaude\cms_dashboards\`.

## REUTILIZAR SIN CAMBIOS

Ninguno. Todos los archivos backend requieren al menos: cambio de shape de error (de
`{"error":{"code","message"}}` a `{"error","mensaje","detalles"}`), o renombrado del rol sembrado,
o traducción de pruebas de pytest a Django `TestCase`. Todos los archivos frontend requieren al
menos: adaptación de `react-bootstrap` (skelleton usa Bootstrap CSS plano) o del path de la API.
No hay copia 1:1 posible en ningún archivo de este repositorio.

## REUTILIZAR CON ADAPTACIONES

| Archivo o módulo (origen) | Clasificación | Motivo | Destino propuesto | Cambios necesarios |
|---|---|---|---|---|
| `backend/apps/users/models.py` | Adaptar | Diseño de modelo válido, greenfield en cms_dashboards | `backend/apps/users/models.py` | Ninguno estructural; se mantiene `AbstractUser` + `status` + `must_change_password` + `created_by`/`updated_by` |
| `backend/apps/authentication/models.py` (`Session`, `LoginAttempt`) | Adaptar | Diseño válido para revocación/expiración de sesión y fuerza bruta | `backend/apps/authentication/models.py` | Se omite `PasswordResetToken` (diferido) |
| `backend/apps/authentication/tokens.py` | Adaptar | Emisión de JWT con claim `sid`, válida | `backend/apps/authentication/tokens.py` | Ninguno |
| `backend/apps/authentication/authentication.py` | Adaptar | `SessionAuthentication(JWTAuthentication)`, válida | `backend/apps/authentication/authentication.py` | Ninguno |
| `backend/apps/authentication/services.py` | Adaptar | Lógica de negocio válida (login/refresh/logout/fuerza bruta) | `backend/apps/authentication/services.py` | Excepciones deben lanzar `cartera.exceptions.CarteraError` en vez de su excepción propia, para obtener el shape de error único del proyecto |
| `backend/apps/authentication/views.py` | Adaptar | Endpoints válidos | `backend/apps/authentication/views.py` | Quitar `/v1/` del prefijo (cms_dashboards no versiona sus endpoints); usar shape de error de cartera |
| `backend/apps/permissions/catalog.py` | Adaptar | Catálogo de permisos válido | `backend/apps/permissions/catalog.py` | Agregar los 7 permisos `dashboard.*` ya definidos en `cartera/permisos.py`, sin renombrarlos |
| `backend/apps/permissions/models.py` (`ModulePermission`) | Adaptar | Patrón válido (ancla `managed=False`) | `backend/apps/permissions/models.py` | Ninguno estructural |
| `backend/apps/permissions/permissions.py` (`HasModulePermission`) | Adaptar | Patrón DRF válido | `backend/apps/permissions/permissions.py` | Auditar denegaciones usando `apps.core.audit.record_audit_event` |
| `backend/apps/roles/views.py` (`RoleViewSet` sobre `Group`) | Adaptar | Patrón válido, sin modelo propio | `backend/apps/roles/views.py` | Shape de error de cartera en validaciones |
| `backend/apps/roles/migrations/0001_initial.py` (seed) | Adaptar | Patrón de siembra válido | `backend/apps/roles/migrations/0002_seed_administrador_general.py` | Renombrar `"Superusuario"` → `"ADMINISTRADOR_GENERAL"` (pedido explícito del usuario) |
| `backend/apps/users/services.py` (`UserAdminService`) | Adaptar | Lógica válida (última cuenta admin activa, revocar sesiones) | `backend/apps/users/services.py` | Shape de error de cartera |
| `backend/apps/users/views.py` (`UserAdminViewSet`) | Adaptar | CRUD administrativo válido | `backend/apps/users/views.py` | Prefijo de URL sin `/v1/` |
| `backend/apps/core/models.py` (`BaseModel`, `AuditLog`) | Adaptar | Diseño genérico válido | `backend/apps/core/models.py` | Ninguno estructural |
| `backend/apps/core/audit.py`/`sensitive_data.py` | Adaptar | Lógica de enmascarado/registro válida | `backend/apps/core/audit.py` | Ninguno |
| `frontend/src/api/client.js` (interceptor de refresh) | Adaptar (diferido a fase frontend) | Lógica de refresh/401 válida | `frontend/src/services/api.js` (extendido) | Leer `err.response?.data?.mensaje` en vez de `err.response?.data?.error?.message`; nombres de claves de `localStorage` propios de cms_dashboards |
| `frontend/src/context/AuthContext.jsx` | Adaptar (diferido) | Lógica de sesión válida | `frontend/src/hooks/useAuth.jsx` o `context/AuthContext.jsx` | Ninguno estructural |
| `frontend/src/components/common/RequirePermission` | Adaptar (diferido) | Guard de ruta por permiso, válido | `frontend/src/components/auth/RequirePermission.jsx` | Reescrito con JSX de react-bootstrap para estados de carga/403 si aplica |
| `frontend/src/components/admin/AdminSidebar/staticAdminMenu.js` | Adaptar (diferido) | Patrón de menú estático filtrado por permiso, válido | `frontend/src/config/adminMenu.js` | Agregar entrada del dashboard de Cartera; reescribir componentes de render con react-bootstrap |
| `frontend/src/pages/Login/Login.jsx` | Adaptar (diferido) | Formulario válido | `frontend/src/pages/authentication/LoginPage.jsx` | Reescrito con `Form`/`Button` de react-bootstrap en vez de clases CSS planas |
| `frontend/src/pages/Admin/Users`, `Roles`, `Permissions` | Adaptar (diferido) | CRUD admin válido | `frontend/src/pages/administration/*` | Reescrito con react-bootstrap |

## REIMPLEMENTAR

| Funcionalidad | Motivo | Notas |
|---|---|---|
| Theming institucional (`SiteTheme`/`ThemeContext`) | Válido conceptualmente, pero debe sembrarse con la paleta actual de `dashboard.css` de cms_dashboards en vez de los defaults de skelleton_base, para no cambiar la identidad visual existente | Diferido a fase de branding |
| Menú administrativo dinámico | skelleton_base lo resuelve estático en frontend; el prompt pide que la API entregue "únicamente los dashboards permitidos" — se necesita un endpoint nuevo (`GET /api/dashboards/authorized`) que no existe en skelleton_base | Diferido a fase de protección de dashboards |
| Auditoría unificada | `DashboardAuditLog` (cartera) y `AuditLog` (nuevo) tienen esquemas distintos; unificarlos requiere una migración de datos de `cartera` que no existe en ningún lado | Diferido, ver `decisions.md` punto 9 |

## NO MIGRAR

| Archivo o módulo | Motivo |
|---|---|
| `requirements/base.txt`, `requirements/dev.txt`, `requirements/prod.txt` | cms_dashboards usa un único `requirements.txt`; no se adopta el split |
| `backend/pytest.ini`, `backend/conftest.py`, `apps/*/tests/*.py` (versión pytest) | Se mantiene Django `TestCase` (decisión del usuario); la lógica se traduce, no se copia el archivo |
| `tests/qa/` (suite BDD de skelleton_base con `pytest-bdd`) | cms_dashboards documenta Gherkin como especificación (no ejecutado por Cucumber/Behave/pytest-bdd); no se adopta el runner, solo se redactará un `.feature` nuevo siguiendo la convención de cms_dashboards |
| `docker-compose.yml`, `docker-compose.prod.yml`, `backend/Dockerfile`, `backend/entrypoint.sh` | cms_dashboards no usa Docker hoy; fuera de alcance de los criterios de aceptación |
| `apps.core` middleware (`RequestIDMiddleware`, `AccessLogMiddleware`), `health/`, `version_views.py` | No los pide ningún criterio de aceptación de esta integración |
| `apps.authentication` flujo de recuperación de contraseña por email (`PasswordResetToken`, `emails.py`) | Diferido, requiere configuración SMTP no solicitada |
| `drf-spectacular` y su configuración | No solicitado; cms_dashboards documenta su API en `docs/api-reference.md` manualmente |
| `.env`, `.env.example` de skelleton_base (valores) | Solo se toman los **nombres** de variables nuevas relevantes (JWT_*), nunca valores ni secretos |
| `frontend/tests/setup.js`, config de Vitest de skelleton_base | cms_dashboards ya tiene su propia configuración de Vitest funcionando; no se sobreescribe |
| `bootstrap-icons` como dependencia nueva | cms_dashboards no usa iconos de librería hoy (usa emoji/texto); no se introduce sin necesidad concreta |
| Cualquier `node_modules/`, `.venv/`, `__pycache__/`, `dist/`, `build/` de skelleton_base | Nunca se copian artefactos generados/instalados |
