# Informe final de migración — integración de skelleton_base en cms_dashboards

Rama: `feature/integracion-skelleton-base`. Repositorio principal: `cms_dashboards` (este
repositorio conserva su historial Git completo; el resultado final vive aquí, no en
`skelleton_base`). Fuente: `skelleton_base` (clon local ya existente como carpeta hermana,
usado solo como referencia de lectura — nunca se copió su `.git`, ni `.env`, ni `node_modules`,
ni `.venv`).

Nota de alcance: en la misma rama y sesión de trabajo también se completó una fase previa,
independiente de esta integración ("Configuración de registros visibles en matrices y tablas" —
paginación configurable de `DetalleTable`/`RecuperadorCausalMatrix`). Los archivos de esa fase
(`backend/cartera/constants.py`, `frontend/src/components/common/Pagination.jsx`,
`frontend/src/hooks/usePaginacionCliente.js`, `Pagination.test.jsx`,
`tests/qa/dashboard_matrices_pagination.feature`, etc.) se listan más abajo diferenciados como
"(no forma parte de la integración con skelleton_base)".

## Archivos creados

**Backend — apps nuevas** (`backend/apps/`, ver `docs/integracion/file_migration_matrix.md`):
`apps/core/{models,audit,admin,apps}.py`, `apps/permissions/{catalog,models,permissions,
authorization,views,urls,apps}.py`, `apps/authentication/{models,tokens,authentication,services,
serializers,views,urls,apps}.py`, `apps/users/{models,serializers,services,filters,signals,views,
urls,admin,apps}.py`, `apps/roles/{serializers,views,urls,apps}.py`, `apps/branding/{catalog,
validators,models,serializers,views,urls,admin,apps}.py`, más `tests.py` en cada app y sus
migraciones (`apps/*/migrations/000*.py`).

**Backend — cartera**: `cartera/dashboard_registry.py` (catálogo de dashboards autorizados),
`cartera/tests/test_dashboard_authorization.py`.

**Frontend — sesión y rutas**: `services/httpClient.js`, `services/authApi.js`,
`services/authService.js`, `context/AuthContext.jsx`, `components/auth/{RequirePermission,
AuthenticatedLayout}.jsx`, `pages/authentication/LoginPage.jsx`, `pages/errors/{ForbiddenPage,
NotFoundPage}.jsx`, `pages/dashboards/DashboardsListPage.jsx`, `routes/AppRoutes.jsx`.

**Frontend — administración**: `services/{usersService,rolesService,permissionsService,
brandingService}.js`, `config/adminMenu.js`, `hooks/useAdminMenu.js`,
`components/admin/{AdminLayout,AdminSidebar}.jsx`, `pages/administration/users/{UsersListPage,
UserFormPage}.jsx`, `pages/administration/roles/{RolesListPage,RoleFormPage}.jsx`,
`pages/administration/permissions/PermissionsPage.jsx`,
`pages/administration/settings/SettingsPage.jsx`, `context/ThemeContext.jsx`.

**Frontend — pruebas nuevas**: `tests/{httpClient,AuthContext,RequirePermission,LoginPage,
AuthenticatedLayout,ThemeContext,adminMenu,AdminSidebar,UsersListPage,UserFormPage,RolesListPage,
RoleFormPage,PermissionsPage,SettingsPage,DashboardsListPage}.test.jsx`.

**Documentación**: `docs/integracion/{skelleton_base_comparison,file_migration_matrix,
integration_plan,decisions,migration_report,post_integration_validation}.md`,
`tests/qa/skelleton_base_integration.feature`,
`tests/qa/acceptance-criteria-traceability-skelleton.md`.

*(No forma parte de esta integración, misma rama)*: `backend/cartera/constants.py`,
`backend/cartera/tests/test_dashboard_authorization.py`¹, `frontend/src/components/common/
Pagination.jsx`, `frontend/src/hooks/usePaginacionCliente.js`,
`frontend/src/tests/Pagination.test.jsx`, `tests/qa/dashboard_matrices_pagination.feature`,
`tests/qa/acceptance-criteria-traceability-pagination.md`.

¹ Aclaración: `test_dashboard_authorization.py` sí es de esta integración (Fase 5); se repite
aquí solo para que la lista de "no forma parte" no quede ambigua sobre `constants.py`, que un
lector podría confundir por estar en la misma carpeta.

## Archivos modificados

**Backend**: `config/settings.py` (`INSTALLED_APPS`, `AUTH_USER_MODEL`, `SIMPLE_JWT`,
`PASSWORD_HASHERS`, `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`/`DEFAULT_PERMISSION_CLASSES`),
`config/urls.py` (rutas `/api/auth/`, `/api/users/`, `/api/roles/`, `/api/permissions/`,
`/api/branding/`), `requirements.txt` (+`djangorestframework-simplejwt`, `+argon2-cffi`),
`.env.example` (+variables `JWT_*`/`LOGIN_*`), `cartera/permisos.py` (resuelve permisos reales,
retira el fallback abierto), `cartera/views.py` (+`permission_classes` en las 11 vistas de
datos), `cartera/dashboard_views.py`/`dashboard_urls.py` (+`DashboardsAuthorizedView`),
`cartera/tests/{test_api,test_dashboard_layout}.py` (autenticación en `setUp`, sin tocar las
aserciones de negocio existentes).

**Frontend**: `App.jsx` (`ThemeProvider`/`AuthProvider`/`BrowserRouter`), `services/api.js` y
`services/dashboardLayoutService.js` (migrados al cliente HTTP compartido con interceptor de
sesión — este segundo era un bug real detectado durante la Fase 5, ver `integration_plan.md`),
`components/auth/AuthenticatedLayout.jsx` (enlace "Administración"), `styles/dashboard.css`
(variables `--color-*`/`--font-*`/`--border-radius`), `routes/AppRoutes.jsx` (rutas `/admin/*`),
`config/adminMenu.js` (ítem "Configuración"), `package.json`/`package-lock.json`
(+`react-router-dom`).

## Archivos eliminados

Ninguno. No se eliminó ni se reescribió ningún archivo existente de `cartera` o de los
componentes de dashboard ya funcionando.

## Funcionalidades migradas (de skelleton_base, adaptadas al contrato de cms_dashboards)

Login/logout/refresh/sesión revocable, hash Argon2, protección de fuerza bruta, modelo de
usuario (`status`/`must_change_password`), roles sobre `Group`, catálogo cerrado de permisos,
rol administrador con el catálogo completo (renombrado a `ADMINISTRADOR_GENERAL`), identidad
institucional (`SiteTheme`) con theming en runtime, menú administrativo estático filtrado por
permiso, páginas de administración de usuarios/roles/permisos/configuración.

## Funcionalidades adaptadas (cambiadas respecto al original)

- Contrato de error: se descartó el shape anidado `{"error":{"code","message"}}` de
  `skelleton_base` en favor del ya existente de `cartera` (`{"error","mensaje","detalles"}`).
- Pruebas backend: de `pytest`/`pytest-django` a Django `TestCase`/`APITestCase`.
- Nombre del rol administrador: `ADMINISTRADOR_GENERAL` (no `"Superusuario"`).
- Prefijos de URL sin versión (`/api/auth/...`, no `/api/v1/auth/...`), consistente con el resto
  de `cartera`.
- Catálogo de permisos ampliado con los 7 `dashboard.*` ya existentes en `cartera`, sin
  renombrarlos.
- Componentes de frontend reescritos con `react-bootstrap` (no el Bootstrap CSS plano de
  `skelleton_base`).

## Funcionalidades no migradas (diferidas, con justificación documentada)

Landing pública, recuperación de contraseña por email, `drf-spectacular`, split
`requirements/base|dev|prod.txt`, Docker, middleware de request-id/access-log y endpoints de
health/version de `apps.core`, unificación de `DashboardAuditLog` con `apps.core.AuditLog`,
sobreescritura de `--bs-primary` de Bootstrap. Ver `file_migration_matrix.md` y `decisions.md`
para el detalle de cada una.

## Conflictos encontrados

- **Historial de migraciones inconsistente al introducir `AUTH_USER_MODEL` propio**: la base de
  datos de desarrollo ya tenía `admin.0001_initial` aplicado contra el modelo de usuario por
  defecto de Django. Se resolvió recreando la base de datos de desarrollo (confirmado
  previamente que sus 5 tablas de `cartera` tenían 0 filas, y con autorización explícita del
  usuario antes de ejecutar el `DROP DATABASE`).
- **Migración de siembra de `ADMINISTRADOR_GENERAL` corriendo antes de que existieran los
  `Permission`/`ContentType`**: en una instalación nueva, la siembra del rol corre en la misma
  invocación de `migrate` que crea `ModulePermission`, antes de que la señal `post_migrate` cree
  los permisos. Resuelto sembrando el `ContentType` y los `Permission` con `get_or_create`
  directamente en la propia migración de datos, en vez de asumir que ya existen.
- **`dashboardLayoutService.js` sin el interceptor de sesión**: detectado en la Fase 5 (ver
  arriba); se corrigió antes de que llegara a producción como una regresión.

## Decisiones tomadas

Las 13 decisiones completas, con contexto/opciones/motivo/impacto, están en
`docs/integracion/decisions.md`. Resumen: apps nuevas conviven con `cartera` sin moverla;
`AUTH_USER_MODEL` propio (greenfield, sin datos que migrar); roles sobre `Group`; catálogo de
permisos unificado; rol `ADMINISTRADOR_GENERAL`; `cartera/permisos.py` retira su fallback abierto
recién en la fase de protección (no antes); un solo contrato de error; JWT sin blacklist nativa
(revocación vía `Session`); auditoría de seguridad y de layout coexisten sin unificar; password
reset por email diferido; un solo `requirements.txt`; Django `TestCase` en vez de pytest;
`react-router-dom@7.18.2` (última versión) pese a una advertencia de `npm audit` que no aplica al
uso real del proyecto.

## Pruebas ejecutadas y aprobadas

- **Backend**: `python manage.py test` → **144/144** (Django `TestCase`/`APITestCase`).
- **Frontend**: `npm run test` (Vitest) → **164/164**.
- **Lint**: `npm run lint` (oxlint) → sin errores; advertencias preexistentes sin relación con
  esta integración (`only-export-components` en archivos que ya exportaban Provider+hook antes
  de esta sesión, un import sin usar preexistente).
- **Manual en navegador** (Chrome real vía automatización): login → sesión persistida tras
  recargar → logout; `/app/dashboards` lista solo los dashboards autorizados; `curl` sin token
  contra `/api/cartera/resumen/<id>` → 401; creación de un rol y un usuario desde la UI
  administrativa, asignación de rol, verificación de que ese usuario ve exactamente lo que su
  rol permite (incluida una denegación real de backend, no solo de UI, al intentar
  `/admin/permissions` sin el permiso); cambio de un color institucional reflejado en vivo sin
  recargar. Sin errores de consola en ningún flujo. Datos de prueba creados durante la
  verificación manual fueron eliminados al finalizar cada fase.

## Pruebas fallidas

Ninguna al cierre de la sesión. (Durante el desarrollo se detectaron y corrigieron fallos
transitorios propios de la implementación — ver el detalle fase por fase en
`integration_plan.md` — ninguno quedó sin resolver.)

## Riesgos pendientes

- El menú administrativo es estático en el frontend; si el catálogo de permisos crece mucho o se
  necesita reordenar el menú sin desplegar, se volvería a evaluar un menú dinámico desde el
  backend (mismo trade-off que ya documentaba `skelleton_base`).
- No se verificó el editor visual del dashboard, el panel de administración, ni la landing
  pública en un dispositivo móvil real durante esta sesión (el diseño responsivo de la landing se
  validó por revisión de CSS — grids con `minmax`, breakpoint a 860px, `scroll-margin-top` — y por
  captura de pantalla en Chrome, no en un dispositivo físico ni con emulación de viewport
  verificada).

## Trabajo futuro completado

Los cuatro puntos que esta sección documentaba como pendientes se implementaron, probaron y
documentaron el **2026-07-31**, en la rama `feature/post-integration-future-work`
(ver `docs/integracion/future_work_completion_report.md` para el informe completo).

- **Auditoría unificada** (Módulo A) — modelo `AuditEvent` (12 dominios), servicio único
  `apps.audit.services.log_event`, migración no destructiva de `apps.core.AuditLog` y
  `cartera.DashboardAuditLog`, pantalla administrativa `/admin/audit` con filtros y exportación
  CSV. Resuelve el riesgo "Unificación de `DashboardAuditLog` con `apps.core.AuditLog`" que este
  documento marcaba como pendiente (decisión #9). Ver `docs/audit/unified_audit.md`.
- **Integración visual con Bootstrap** (Módulo B) — colores institucionales (incluidos los 5
  nuevos campos semánticos `success`/`danger`/`warning`/`info`/`button_text`) conectados a los
  componentes reales de Bootstrap (`.btn-*`, `.btn-outline-*`, `.bg-*`, `.text-*`, `.alert-*`,
  enlaces, foco y casillas) mediante una hoja de estilos inyectada en tiempo de ejecución —
  sobreescribir solo variables en `:root` no alcanza con el Bootstrap precompilado que usa el
  proyecto (ver hallazgo documentado en `docs/frontend/bootstrap_theme.md`). Aviso de contraste
  WCAG AA no bloqueante en `/admin/settings`.
- **Landing pública profesional** (Módulo C) — `/` ya no redirige automáticamente; renderiza una
  landing completa (hero, Plataforma, Dashboards con 10 áreas de ejemplo sin acceso real,
  Funcionamiento con diagrama de flujo, Seguridad, Beneficios, CTA, pie de página) con menú
  sticky, scroll suave y resaltado de sección activa. Ver `docs/public/landing_page.md`.
- **Recuperación de contraseña por correo** (Módulo D) — flujo completo
  solicitud/token/correo/restablecimiento, con auditoría, rate limiting, y un comando QA para
  pruebas manuales. Validado con un envío real de control a `dpenarreta@grupolaar.com` (evento de
  auditoría `PASSWORD_RESET_EMAIL_SENT` id 37). Ver `docs/authentication/password_recovery.md`.

Pruebas: 173 pruebas backend, 207 pruebas frontend, todas en verde tras completar los cuatro
módulos (ver `future_work_completion_report.md` para el detalle por módulo).

## Trabajo futuro

Sugerido, no comprometido: menú administrativo dinámico si el catálogo de permisos crece mucho,
Docker para desarrollo/despliegue si el equipo lo adopta, verificación en un dispositivo móvil
real (landing, editor visual, panel de administración), un editor visual completo para el
contenido de la landing (explícitamente fuera de alcance de Módulo C).
