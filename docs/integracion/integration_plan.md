# Plan de integración: cms_dashboards + skelleton_base

Ver `skelleton_base_comparison.md` y `file_migration_matrix.md` para el detalle de diferencias y
clasificación de archivos. Ver `decisions.md` para el razonamiento de cada decisión de arquitectura.

Ritmo acordado con el usuario: ejecución por fases con checkpoint. Este documento cubre las 11
fases completas; el estado de cada una se actualiza a medida que se ejecutan.

## Fase 0 — Respaldo y preparación
- **Objetivo**: no perder trabajo, tener rama de integración, generar los documentos obligatorios.
- **Archivos afectados**: `docs/integracion/*.md` (nuevos).
- **Dependencias**: ninguna.
- **Riesgos**: ninguno (solo lectura + documentación + rama nueva).
- **Pruebas requeridas**: `git status`/`git log -1`/`git branch --show-current` antes y después.
- **Criterio de reversión**: `git checkout main` (la rama nueva no afecta `main`).
- **Resultado esperado**: rama `feature/integracion-skelleton-base` creada; 4 documentos creados.
- **Estado**: ✅ Completada en esta sesión.

## Fase 1 — Consolidación de dependencias
- **Objetivo**: agregar `djangorestframework-simplejwt` y `argon2-cffi` sin romper el resto.
- **Archivos afectados**: `backend/requirements.txt`, `backend/.env.example`.
- **Dependencias**: Fase 0.
- **Riesgos**: bajo (librerías aisladas, no reemplazan nada existente).
- **Pruebas requeridas**: `pip install -r requirements.txt` sin errores; `manage.py check` sin errores.
- **Criterio de reversión**: revertir el diff de `requirements.txt`/`.env.example`.
- **Resultado esperado**: dependencias instaladas en `backend/.venv`.
- **Estado**: ✅ Completada en esta sesión.

## Fase 2 — Integración backend de autenticación, usuarios, roles y permisos
- **Objetivo**: modelo de usuario propio, JWT, roles/permisos reales, sin activar aún el bloqueo
  de los endpoints de `cartera`.
- **Archivos afectados**: `backend/apps/{core,permissions,authentication,users,roles}/**`,
  `backend/config/settings.py`, `backend/config/urls.py`, `backend/cartera/permisos.py`.
- **Dependencias**: Fase 1.
- **Riesgos**: medio — cambiar `AUTH_USER_MODEL` requiere migraciones limpias (mitigado: sin datos
  de producción, confirmado con el usuario). Añadir apps nuevas a `INSTALLED_APPS` no debe alterar
  el comportamiento de `cartera` (mitigado: `DEFAULT_PERMISSION_CLASSES` no cambia en esta fase).
- **Pruebas requeridas**: 77 pruebas existentes de `cartera` en verde + pruebas nuevas de
  `apps.*` (login, refresh, logout, fuerza bruta, CRUD usuarios/roles, catálogo de permisos).
- **Criterio de reversión**: `git revert` de los commits de esta fase; `manage.py migrate
  <app> zero` por app nueva si hiciera falta deshacer en una base compartida (no aplica en dev).
- **Resultado esperado**: `POST /api/auth/login/` funcional; `cartera` sigue accesible sin token.
- **Estado**: ✅ Completada en esta sesión (ver detalle de implementación al final del documento).
  Verificado: 120/120 pruebas Django en verde (77 de `cartera` sin modificar su comportamiento +
  43 nuevas de `apps.*`), `makemigrations --check` sin cambios pendientes,
  `GET /api/cartera/causales/<uuid>` sin token responde 404 (carga inexistente) y no 401 —
  confirma que `cartera` sigue abierta a propósito en esta fase.

## Fase 3 — Identidad institucional (branding)
- **Objetivo**: modelo `SiteTheme` + endpoint público de tema actual, sembrado desde la paleta
  actual de `dashboard.css` (no cambia la identidad visual el día 1).
- **Archivos afectados**: `backend/apps/branding/**`, migración de datos de siembra,
  `backend/config/settings.py`/`urls.py`.
- **Dependencias**: Fase 2 (usa el mismo patrón de permisos `configuracion.ver`/`configuracion.editar`,
  ya incluidos en el catálogo de la Fase 2).
- **Riesgos**: bajo — es un modelo nuevo, sin datos previos que migrar.
- **Pruebas requeridas**: obtener tema público sin auth; actualizar tema requiere
  `configuracion.editar`; restablecer vuelve a los valores sembrados.
- **Criterio de reversión**: `git revert`; la app es aislada.
- **Resultado esperado**: `GET /api/branding/current/` devuelve la paleta actual de cms_dashboards.
- **Estado**: ✅ Completada. `apps/branding` (modelo singleton `SiteTheme` con `pk=1` forzado,
  catálogo de fuentes/radios en `catalog.py`, `DEFAULT_THEME` sembrado desde
  `frontend/src/styles/dashboard.css`: `color_primary=#2a78d6` ya usado como color de foco/serie
  principal, `color_background=#eeeeee` (`--page-plane`), `color_headings`/`color_text=#000000`).
  Endpoints: `GET /api/branding/current` (público), `GET|PATCH /api/branding/admin`
  (`configuracion.ver`/`configuracion.editar`), `POST /api/branding/admin/reset`,
  `GET /api/branding/admin/options`. 131/131 pruebas Django en verde (120 previas + 11 nuevas).
  Nota: `site_name`/`short_name` se sembraron desde el `<title>` actual de `index.html`
  ("Dashboard de Cartera"/"Cartera"); `logo_url`/`favicon_url` quedan vacíos (el frontend seguirá
  usando `/favicon.svg` como fallback estático hasta que un administrador cargue uno real, en la
  Fase 7 de integración visual).

## Fase 4 — Frontend de sesión y rutas
- **Objetivo**: `react-router-dom`, `AuthContext`, interceptor Axios con refresh automático,
  `RequirePermission`, páginas de login/perfil.
- **Archivos afectados**: `frontend/package.json`, `frontend/src/main.jsx`/`App.jsx` (introduce
  `BrowserRouter`), `frontend/src/context/AuthContext.jsx` (nuevo), `frontend/src/services/api.js`
  (interceptores), `frontend/src/routes/AppRoutes.jsx` (nuevo), `frontend/src/pages/authentication/*`.
- **Dependencias**: Fase 2 (necesita los endpoints de `/api/auth/*` ya funcionando).
- **Riesgos**: alto — es el cambio estructural más grande del frontend (de "una sola página" a
  "app con rutas"). Verificar compatibilidad de `react-router-dom` con React 19 antes de fijar
  versión; probar en navegador, no solo en Vitest.
- **Pruebas requeridas**: login exitoso/fallido, persistencia de sesión tras recargar, logout,
  interceptor de token expirado, `RequirePermission` en sus 4 estados (inicializando, no
  autenticado, sin permiso, con permiso).
- **Criterio de reversión**: la app puede seguir funcionando como "una sola página" si se envuelve
  `CarteraDashboardPage` en una ruta por defecto mientras se prueba el enrutador en paralelo.
- **Resultado esperado**: `/login` funcional; `/app/dashboards/cartera` muestra el dashboard actual
  ya envuelto en el nuevo layout autenticado.
- **Estado**: ✅ Completada. `react-router-dom@7.18.2` (ver decisions.md #13),
  `frontend/src/services/httpClient.js` (cliente Axios compartido con interceptor de
  adjuntar-token + refresh automático en 401 + redirección a `/login`, adaptado a leer
  `err.response?.data?.mensaje`/`detail`, el contrato de error de `cartera`, no el anidado de
  skelleton_base), `frontend/src/services/api.js` (cartera) ahora usa ese mismo cliente
  compartido — listo para cuando la Fase 5 exija el token en esos endpoints.
  `frontend/src/context/AuthContext.jsx`, `frontend/src/components/auth/RequirePermission.jsx`,
  `frontend/src/components/auth/AuthenticatedLayout.jsx` (barra superior con usuario + "Cerrar
  sesión"), `frontend/src/pages/authentication/LoginPage.jsx`,
  `frontend/src/routes/AppRoutes.jsx`. `CarteraDashboardPage` no se modificó — solo se envolvió
  en la ruta `/app/dashboards/cartera` protegida por `dashboard.view`.
  Verificado: 131/131 pruebas Vitest en verde (108 previas + 23 nuevas), `npm run lint` sin
  errores nuevos, y **prueba manual en navegador real** (Chrome vía claude-in-chrome): login con
  usuario de prueba → redirección a `/app/dashboards/cartera` → barra superior con "admin"/
  "Cerrar sesión" → recarga completa de página preserva la sesión (`GET /auth/me` con el token
  guardado) → "Cerrar sesión" vuelve a `/login` → sin errores de consola en ningún paso.

## Fase 5 — Protección de dashboards
- **Objetivo**: activar `dashboard.view`/`dashboard.edit`/etc. de verdad sobre los endpoints de
  `cartera`, y exponer `GET /api/dashboards/authorized`.
- **Archivos afectados**: `backend/config/settings.py` (`DEFAULT_PERMISSION_CLASSES`),
  `backend/cartera/views.py`/`dashboard_views.py` (permission_classes explícitos),
  `backend/cartera/dashboard_registry.py` (nuevo, catálogo en código igual que
  `dashboard_layout.py`), `frontend/src/pages/dashboards/*`.
- **Dependencias**: Fase 4 (el frontend ya debe poder loguearse antes de que el backend empiece a
  exigir token, o el dashboard quedaría inaccesible).
- **Riesgos**: alto — es el punto donde el dashboard "se cierra"; requiere probar exhaustivamente
  que un usuario autenticado con permiso sigue viendo todo igual que antes.
- **Pruebas requeridas**: 401 sin token, 403 sin permiso, 200 con permiso; `ADMINISTRADOR_GENERAL`
  ve todos los dashboards; regresión completa de KPIs/gráficos/matrices/filtros/paginación.
- **Criterio de reversión**: revertir `DEFAULT_PERMISSION_CLASSES` a su valor anterior restaura el
  acceso abierto de inmediato.
- **Resultado esperado**: dashboard de Cartera protegido, sin regresiones funcionales.
- **Estado**: ✅ Completada.
  - `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` activado globalmente
    (`config/settings.py`); las 11 vistas de datos de `cartera/views.py` (validar-archivo,
    procesar, resumen, top-clientes, pareto-ciudades, recuperadores, causales,
    recuperadores-causales, detalle, exportar, archivo) ahora exigen además el permiso
    `dashboard.view` vía `apps.permissions.permissions.require_permission` (mismo mecanismo ya
    usado por `apps.users`/`apps.roles`/`apps.branding` — una sola implementación de
    autorización, no una paralela dentro de `cartera`).
  - `cartera/permisos.py`: se retiró el fallback "todo concedido sin autenticar" (ahora fallo
    cerrado: sin usuario, todos los permisos son `False`). `dashboard_views.py` no necesitó
    cambios — ya validaba `tiene_permiso` manualmente y ahora ese chequeo corre siempre sobre un
    usuario real.
  - Nuevo `cartera/dashboard_registry.py` + `GET /api/dashboards/authorized` (antes de los
    patrones `<slug:dashboard_id>/...` en `dashboard_urls.py`): devuelve solo los dashboards cuyo
    permiso requerido tiene el usuario autenticado — hoy solo `cartera`, listo para crecer sin
    tocar el frontend.
  - **Bug encontrado y corregido durante esta fase**: `frontend/src/services/dashboardLayoutService.js`
    creaba su propia instancia de Axios (`axios.create(...)`) en vez de reutilizar
    `httpClient.createApiClient` — sin el interceptor de token, el editor visual del dashboard
    habría empezado a fallar con 401 en cuanto se activó `IsAuthenticated`. Corregido para usar el
    mismo cliente compartido que `services/api.js`.
  - Frontend: `frontend/src/pages/dashboards/DashboardsListPage.jsx` (nueva ruta
    `/app/dashboards`, consume `GET /api/dashboards/authorized`, sin hardcodear qué dashboards
    existen — solo el mapeo `dashboard_id -> ruta de React`, inevitable con un solo dashboard
    implementado); `AuthenticatedLayout` enlaza su marca a esa ruta.
  - Verificado: 142/142 pruebas Django (131 previas + 11 nuevas de
    `test_dashboard_authorization.py`: 401 sin token, 403 autenticado sin permiso, 200 con
    permiso individual, 200 vía grupo `ADMINISTRADOR_GENERAL`, superusuario) + 136/136 Vitest.
    Prueba manual en navegador: `GET /api/cartera/resumen/<id>` sin token → 401 confirmado por
    `curl`; login → `/app/dashboards` lista "Dashboard de cartera" → clic navega a
    `/app/dashboards/cartera` → carga normalmente; sin errores de consola.

## Fase 6 — Menú administrativo
- **Objetivo**: menú autenticado + menú administrativo, generados según permisos.
- **Archivos afectados**: `frontend/src/config/adminMenu.js` (nuevo), `frontend/src/hooks/useAdminMenu.js`,
  componentes de sidebar/navegación.
- **Dependencias**: Fase 5 (necesita saber qué dashboards están autorizados).
- **Riesgos**: bajo — es composición de UI sobre datos ya disponibles.
- **Pruebas requeridas**: menú no muestra ítems sin permiso; incluye el dashboard de Cartera.
- **Criterio de reversión**: trivial (componente aislado).
- **Resultado esperado**: menú administrativo con Usuarios/Roles/Permisos/Configuración/Dashboards.
- **Estado**: ✅ Completada.
  - `frontend/src/config/adminMenu.js` (menú estático filtrado por permiso, mismo patrón que
    trae skelleton_base) + `hooks/useAdminMenu.js` + `components/admin/{AdminSidebar,AdminLayout}.jsx`.
  - Servicios `usersService.js`, `rolesService.js`, `permissionsService.js` (sobre `authApi`, ya
    con interceptor de sesión).
  - Páginas completas de administración, todas con react-bootstrap (no el Bootstrap CSS plano de
    skelleton_base): `UsersListPage`/`UserFormPage` (crear, editar, habilitar/deshabilitar,
    asignar roles y permisos directos), `RolesListPage`/`RoleFormPage` (crear, editar, eliminar
    con confirmación, checkboxes de permisos agrupados por módulo), `PermissionsPage` (catálogo
    de solo lectura).
  - Rutas anidadas bajo `/admin` (dentro de `AuthenticatedLayout`, reutilizando la misma barra
    superior), cada una protegida por `RequirePermission` con su permiso específico
    (`usuarios.ver`/`usuarios.crear`/`usuarios.editar`, `roles.ver`/`roles.editar`,
    `permisos.ver`) — la protección real sigue siendo del backend (`require_permission(...)` en
    cada vista), esto solo evita mostrar enlaces a secciones sin acceso.
  - Enlace "Administración" en la barra superior, visible solo si el usuario tiene al menos un
    permiso administrativo.
  - Verificado: 157/157 pruebas Vitest (21 nuevas: `adminMenu`, `AdminSidebar`, `UsersListPage`,
    `UserFormPage`, `RolesListPage`, `RoleFormPage`, `PermissionsPage`) + 142/142 Django (sin
    cambios backend en esta fase, ya cubierto en la Fase 2/5). Prueba manual completa en
    navegador: creado un rol "Cobranzas" (usuarios.ver + roles.ver + dashboard.view) desde la UI,
    creado un usuario, asignado el rol, verificado que ese usuario ve el dashboard de Cartera y
    las secciones Usuarios/Roles pero recibe 403 real (backend, no solo UI) al entrar a
    `/admin/permissions` sin `permisos.ver`. Sin errores de consola. Datos de prueba eliminados
    al terminar.

## Fase 7 — Configuración institucional (integración visual)
- **Objetivo**: que login, landing (si se construye) y panel autenticado consuman `ThemeContext`.
- **Archivos afectados**: `frontend/src/context/ThemeContext.jsx` (nuevo), `dashboard.css`.
- **Dependencias**: Fase 3.
- **Riesgos**: bajo.
- **Pruebas requeridas**: cambiar un color en `/admin` se refleja en login y dashboard.
- **Estado**: ✅ Completada.
  - `frontend/src/context/ThemeContext.jsx`: en el montaje de toda la app (incluida la landing de
    login, sin sesión) consulta `GET /api/branding/current` (público) y aplica el tema como
    variables CSS sobre `document.documentElement` (`--color-primary`, `--color-background`,
    etc.), además de `document.title` y el favicon — si la consulta falla, no rompe nada: se
    queda con los valores estáticos ya definidos en `dashboard.css`.
  - `frontend/src/styles/dashboard.css`: nuevas variables `--color-*`/`--font-*`/`--border-radius`
    con los mismos valores que ya tenía la app (`--color-primary` = el mismo azul que
    `--series-1`/el foco de teclado, `--color-background` = el mismo gris que `--page-plane`) —
    activar branding no cambió nada visualmente el día 1. `body`, el foco de teclado
    (`:focus-visible`) y el radio de borde de `.kpi-card`/`.chart-panel` ahora leen de estas
    variables en vez de valores fijos.
  - **Decisión explícita de alcance**: no se sobreescribe `--bs-primary` de Bootstrap (color de
    botones/enlaces por defecto) para no introducir un cambio visual no solicitado en todos los
    botones de la aplicación con un solo interruptor; `color_buttons`/`color_links` ya se
    guardan y se devuelven por la API, listos para conectarse en un incremento futuro si se
    decide explícitamente.
  - `frontend/src/pages/administration/settings/SettingsPage.jsx` (nueva, en
    `/admin/settings`, permiso `configuracion.ver`/`configuracion.editar`): edita nombre/logo/
    favicon/8 colores (selector visual + hex)/tipografía/radio de bordes, con "Restablecer"
    (con confirmación). Al guardar o restablecer, llama a `reloadTheme()` para que el cambio se
    vea de inmediato sin recargar la página. Ítem nuevo "Configuración" en el menú administrativo.
  - Verificado: 164/164 pruebas Vitest (8 nuevas: `ThemeContext`, `SettingsPage`) + 142/142
    Django (sin cambios backend en esta fase). Prueba manual en navegador: `document.title` y
    `--color-primary` ya aplicados en `/login` sin sesión; cambiado "Color principal" a `#aa1155`
    desde `/admin/settings`, guardado, y la variable CSS se actualizó en vivo sin recargar la
    página; restablecido a los valores por defecto. Sin errores de consola. No se hizo clic en el
    botón "Restablecer" real en el navegador (dispara `window.confirm` nativo, que bloquearía la
    sesión de automatización) — ese flujo ya está cubierto por pruebas automatizadas que mockean
    `window.confirm`; el restablecimiento se verificó directamente contra el backend.

## Fase 8 — Base de datos y migraciones (consolidación final)
- **Objetivo**: revisar que todas las migraciones nuevas apliquen limpiamente en un entorno nuevo
  y documentar el orden de `migrate`.
- **Archivos afectados**: ninguno nuevo, solo verificación.
- **Riesgos**: bajo (ya se valida incrementalmente en cada fase).
- **Estado**: ✅ Completada. `manage.py makemigrations --check --dry-run` → "No changes detected";
  `manage.py showmigrations` → 0 migraciones sin aplicar. No se requirió trabajo adicional: cada
  fase (2, 3, 5) ya validó sus propias migraciones al ejecutarse.

## Fase 9 — Pruebas (regresión + seguridad + Gherkin)
- **Objetivo**: `tests/qa/skelleton_base_integration.feature`, pruebas de seguridad (401/403,
  fuerza bruta, expiración), regresión completa de `cartera`.
- **Archivos afectados**: `tests/qa/skelleton_base_integration.feature` (nuevo),
  `docs/integracion/acceptance-criteria-traceability-skelleton.md` (nuevo).
- **Dependencias**: Fases 2, 4, 5.
- **Estado**: ✅ Completada. `tests/qa/skelleton_base_integration.feature` (15 escenarios, tal
  como los especificó el usuario) + `tests/qa/acceptance-criteria-traceability-skelleton.md`.
  Se detectó y corrigió un hueco de cobertura real: no había ninguna prueba de que modificar los
  permisos de un rol quedara auditado (AC-INT-013) — se agregaron
  `apps/roles/tests.py::test_modificar_permisos_de_un_rol_registra_auditoria` y
  `test_crear_rol_registra_auditoria`. 144/144 pruebas Django en verde. AC-INT-003
  (landing) y la cláusula de landing de AC-INT-014 quedan documentadas como "no aplica" por la
  decisión explícita de omitir la landing en esta ronda (ver traceability doc), no como
  aprobadas silenciosamente.

## Fase 10 — Documentación
- **Objetivo**: `README.md` consolidado, `migration_report.md`, `post_integration_validation.md`.
- **Dependencias**: todas las anteriores.
- **Estado**: ✅ Completada. `README.md` actualizado (arquitectura consolidada, apps nuevas,
  instalación con `createsuperuser`, variables de entorno JWT, endpoints de auth/usuarios/roles/
  permisos/branding, sección de seguridad ampliada, limitaciones conocidas separadas entre las
  propias de `cartera` y las de esta integración). Creados
  `docs/integracion/migration_report.md` (archivos creados/modificados, funcionalidades
  migradas/adaptadas/no migradas, conflictos y su resolución, decisiones, pruebas ejecutadas,
  riesgos pendientes, trabajo futuro) y `docs/integracion/post_integration_validation.md`
  (checklist honesto contra los criterios de "no terminado" de la sección 31 del prompt
  original).

---

## Detalle de implementación — Fase 2 (ejecutada en esta sesión)

Ver commits en la rama `feature/integracion-skelleton-base` y `docs/integracion/decisions.md`
para el razonamiento. Resumen de archivos creados:

- `backend/apps/__init__.py`
- `backend/apps/core/{__init__.py,apps.py,models.py,audit.py,admin.py,migrations/}`
- `backend/apps/permissions/{__init__.py,apps.py,models.py,catalog.py,permissions.py,authorization.py,views.py,urls.py,migrations/}`
- `backend/apps/authentication/{__init__.py,apps.py,models.py,tokens.py,authentication.py,services.py,serializers.py,views.py,urls.py,migrations/}`
- `backend/apps/users/{__init__.py,apps.py,models.py,serializers.py,services.py,filters.py,signals.py,views.py,urls.py,admin.py,migrations/}`
- `backend/apps/roles/{__init__.py,apps.py,serializers.py,views.py,urls.py,migrations/}`
- `backend/apps/*/tests.py` (Django `TestCase`/`APITestCase`)
- Modificados: `backend/config/settings.py`, `backend/config/urls.py`, `backend/requirements.txt`,
  `backend/.env.example`, `backend/cartera/permisos.py`.
