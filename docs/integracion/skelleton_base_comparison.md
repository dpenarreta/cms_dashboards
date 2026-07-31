# Comparación cms_dashboards vs. skelleton_base

Fuente: análisis de `C:\Users\itinnouio\ProyectosClaude\cms_dashboards` (rama
`feature/integracion-skelleton-base`) contra `C:\Users\itinnouio\ProyectosClaude\skelleton_base`
(commit `a9896f1`, clon local ya existente como carpeta hermana, usado solo como fuente de
lectura — no se copió su `.git`, no se copiaron `.env`/`.env.example` con valores reales, no se
copiaron `node_modules`/`.venv`/builds).

## Matriz de diferencias

| Categoría | CMS Dashboards | Skelleton Base | Diferencia | Riesgo | Acción propuesta |
|---|---|---|---|---|---|
| React | 19.2.7 + react-bootstrap 2.10 | 18.3.1 + Bootstrap CSS puro (sin react-bootstrap) | Versión mayor distinta + paradigma de UI distinto (componentes JSX vs. clases CSS) | Medio (verificar peer-deps de `react-router-dom@6.28`/`@testing-library/react@16` con React 19) | Mantener React 19 de cms_dashboards; reescribir páginas/componentes portados con `react-bootstrap` en vez de adoptar el Bootstrap CSS plano |
| Bundler | Vite 8.1 | Vite 6.0 | Menor, compatible | Bajo | Mantener Vite 8 de cms_dashboards |
| Enrutamiento frontend | Ninguno (App.jsx renderiza un único componente) | `react-router-dom` 6.28, rutas públicas planas + `/admin` anidado con `Outlet` | cms_dashboards no tiene enrutador | Medio (introduce un cambio estructural grande) | Adoptar `react-router-dom`; diferido a la fase de frontend completo |
| Estado global frontend | Hooks locales por página (`useCarteraDashboard`, etc.) | Context API (`AuthContext`, `ThemeContext`, `AppearanceContext`, `UnsavedChangesContext`) | Compatible (ambos son patrones nativos de React, no hay Redux en ninguno) | Bajo | Añadir `AuthContext` como un contexto más, conviviendo con los hooks existentes de cartera |
| Cliente HTTP | Axios, `services/api.js` simple sin interceptores | Axios, `api/client.js` con interceptores de token + refresh automático en 401 | Skelleton aporta funcionalidad que cms_dashboards no tiene | Bajo | Extender `api.js` con los interceptores (adaptados al shape de error de cartera); diferido a fase frontend |
| Django | 5.0.x | 5.1.15 | Menor, compatible | Bajo | Mantener el pin `>=5.0,<5.1` de cms_dashboards (SQL Server vía mssql-django ya validado en esa línea) |
| DRF | 3.15.x | 3.15.2 | Prácticamente igual | Bajo | Sin cambios |
| Base de datos | SQL Server vía `mssql-django`/`pyodbc` | SQL Server vía `mssql-django`/`pyodbc` | Igual motor y driver | Bajo | Consolidar en una sola configuración (la de cms_dashboards, con `DB_NAME=cms_dashboards`) |
| Autenticación | Inexistente (`permisos.py` concede todo siempre) | JWT completo (`djangorestframework-simplejwt`) + hash Argon2 + sesiones propias + fuerza bruta | cms_dashboards no tiene nada que preservar aquí | Bajo (sin datos ni usuarios existentes que migrar) | Adoptar el sistema de `skelleton_base` casi sin cambios |
| Usuario | No existe modelo custom (nunca se usó `auth.User`) | `User(AbstractUser, BaseModel)` con `status`/`must_change_password`/auditoría de creador | Sin conflicto real (greenfield) | Bajo | Adoptar `AUTH_USER_MODEL = 'users.User'` de skelleton_base tal cual |
| Roles | No existen | `django.contrib.auth.models.Group` (sin tabla propia) | Sin conflicto | Bajo | Adoptar tal cual, renombrando el rol sembrado a `ADMINISTRADOR_GENERAL` (pedido explícito del usuario) en vez de "Superusuario" |
| Permisos | 7 constantes de cadena (`dashboard.*`) verificadas por un stub que siempre concede | Catálogo cerrado de 13 permisos anclado a `ModulePermission` (`auth.Permission` reales) | Dos sistemas de nombres de permiso que deben convivir | Medio | Fusionar: agregar los 7 permisos de `dashboard.*` al mismo catálogo/`ModulePermission`, sin renombrarlos, para no tocar los call-sites de `cartera` |
| Menú | Ninguno | Estático en frontend (`staticAdminMenu.js`), filtrado por `user.permissions` | cms_dashboards no tiene nada que preservar | Bajo | Adoptar el patrón; diferido a fase de menú |
| Identidad institucional | CSS fijo (`dashboard.css`, variables `--series-*`, sin modelo) | `SiteTheme` (singleton) + `ThemeContext` dinámico + fallback CSS "de arranque en frío" | cms_dashboards no tiene modelo, solo valores fijos | Bajo (no hay nada que perder, solo sembrar el modelo con la paleta actual) | Adoptar `SiteTheme`, sembrado desde los valores actuales de `dashboard.css` para no cambiar la identidad visual el día 1; diferido |
| Auditoría | `DashboardAuditLog` (específico de cambios de layout del editor visual) | `AuditLog` genérico (login, cambios de usuario/rol/permiso, acceso denegado) | Dominios distintos, no directamente equivalentes | Medio (decidir si unificar) | Coexistencia documentada en esta fase; unificación evaluada en una fase posterior explícita, no se declara resuelta prematuramente |
| Landing pública / menú público | Inexistente (`App.jsx` renderiza directo el dashboard) | Inexistente (solo `Home.jsx` con un link a login) | Ninguno de los dos proyectos la tiene realmente | Bajo | Fuera de alcance por decisión explícita del usuario; la app entra a `/login` (diferido a fase frontend) |
| Testing backend | Django `TestCase`/`APITestCase`, `manage.py test`, 77 pruebas | `pytest` + `pytest-django` + `pytest-bdd`, `factory-boy` | Frameworks distintos | Medio (duplicar tooling si se traen ambos) | Mantener Django `TestCase` (decisión explícita del usuario); reescribir la lógica de las pruebas portadas en ese estilo |
| Testing frontend | Vitest + RTL | Vitest + RTL | Igual | Bajo | Sin cambios |
| Exportación de datos | CSV/XLSX server-side con antiinyección de fórmulas | No aplica (skelleton no tiene dominio de negocio) | N/A | N/A | Sin cambios |
| CORS/CSRF | `django-cors-headers`, `CSRF_TRUSTED_ORIGINS` = mismos orígenes de CORS | `django-cors-headers`, CSRF solo relevante para el admin de Django (API es JWT sin cookies) | Compatible | Bajo | Mantener configuración de cms_dashboards, ampliar orígenes si el frontend cambia de puerto |
| Contrato de error API | `{"error", "mensaje", "detalles"}` (propio) + fallback a `{"detail": ...}` de DRF | `{"error": {"code", "message", "details"}}` (anidado) | Dos contratos incompatibles | Medio | Se descarta el contrato anidado de skelleton_base; todo el backend usa el contrato ya existente de cartera |
| Variables de entorno | `.env`/`.env.example` simple, sin JWT | `.env.example` con `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, etc. | Complementarias, no conflictivas | Bajo | Fusionar en un único `.env.example` |
| Docker | Ninguno | `docker-compose.yml` (solo SQL Server) + `docker-compose.prod.yml` (stack completo) | cms_dashboards no tiene Docker | Bajo | No se adopta en esta fase (no lo pide ningún criterio de aceptación); queda como trabajo futuro opcional |

## Qué se mantiene de cms_dashboards

- Toda la lógica de negocio de `cartera` (ingesta de Excel, cálculo de KPIs, agregaciones,
  matrices, filtros, exportación, editor visual de dashboards, paginación configurable) — intacta,
  sin mover de carpeta.
- React 19, Vite, react-bootstrap, Recharts, estructura de `frontend/src/`.
- El contrato de error de la API (`cartera.exceptions.cartera_exception_handler`).
- Django `TestCase` como único framework de pruebas backend.
- Un único `requirements.txt` (no se adopta el split `base/dev/prod` de skelleton_base).

## Qué se incorpora desde skelleton_base

- Modelo de usuario, autenticación JWT, hash Argon2, sesiones, protección de fuerza bruta.
- Catálogo de permisos + roles basados en `Group`.
- (Diferido) Theming institucional dinámico, menú administrativo, frontend de auth/admin.

## Qué debe reescribirse

- Las vistas/servicios de autenticación y administración de usuarios/roles: misma lógica de
  negocio, pero emitiendo el contrato de error de cartera en vez del contrato anidado propio de
  skelleton_base.
- Las pruebas backend de skelleton_base: de pytest a Django `TestCase`/`APITestCase`.
- (Diferido) Los componentes de frontend de auth/admin: de Bootstrap CSS plano a `react-bootstrap`.

## Qué puede reutilizarse sin cambios (conceptualmente, adaptado a Django puro sin pytest)

- El diseño de modelos (`User`, `Session`, `LoginAttempt`, `ModulePermission`) y el catálogo de
  permisos como estructura de datos.
- El patrón de migración de datos para sembrar un rol con el catálogo completo de permisos
  (renombrado a `ADMINISTRADOR_GENERAL`).
- El patrón `SessionAuthentication(JWTAuthentication)` con claim `sid` para poder revocar sesiones
  sin depender de la blacklist nativa de simplejwt.

## Qué debe descartarse

- El split de `requirements/base|dev|prod.txt`.
- El contrato de error anidado `{"error": {"code", "message"}}`.
- El Bootstrap CSS plano como sistema de componentes (se reescribe con react-bootstrap).
- `drf-spectacular` (documentación OpenAPI automática) — no lo pide ningún criterio de aceptación;
  se puede añadir después sin riesgo si se necesita.
- El middleware de request-id/access-log y los endpoints de health/version de `apps.core` — fuera
  de alcance de los criterios de aceptación de esta integración.
- La recuperación de contraseña por email (requiere configuración SMTP no solicitada
  explícitamente) — diferida.

## Qué requiere migración

- Ninguna migración de **datos** (el usuario confirmó que no hay datos de producción). Sí hay
  migraciones de **esquema** nuevas: `AUTH_USER_MODEL` propio, tablas de `apps.*`, y la migración
  de datos que siembra el catálogo de permisos + el rol `ADMINISTRADOR_GENERAL`.

## Qué genera conflictos

- Ninguno bloqueante: al no existir autenticación previa en cms_dashboards, no hay dos sistemas de
  auth compitiendo. El único punto de fricción real es el contrato de error (resuelto arriba) y el
  nombre del rol sembrado (resuelto: `ADMINISTRADOR_GENERAL`).

## Qué dependencias deben actualizarse

- Backend: agregar `djangorestframework-simplejwt`, `argon2-cffi` a `requirements.txt`.
- Frontend (diferido a la fase de frontend): agregar `react-router-dom`; verificar compatibilidad
  con React 19 antes de fijar versión.

## Qué modelos deben unificarse

- Ninguno tiene equivalente previo en cms_dashboards (usuarios/roles/permisos son 100% nuevos). El
  único modelo con posible solapamiento conceptual es `DashboardAuditLog` (cartera) vs. `AuditLog`
  (nuevo) — **no se unifican en esta fase** (ver decisión 9 en `decisions.md`).

## Qué rutas deben cambiarse

- Ninguna ruta existente de `cartera`/`dashboards` cambia. Se agregan rutas nuevas bajo
  `/api/auth/`, `/api/users/`, `/api/roles/`, `/api/permissions/`.

## Qué pruebas deben actualizarse

- Ninguna prueba existente de `cartera` (77) debe modificarse — deben seguir pasando exactamente
  igual. Se agregan pruebas nuevas para cada app de `apps.*`.
