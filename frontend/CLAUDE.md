# Frontend (React 19 + Vite)

Hereda `../CLAUDE.md` (comandos base, contrato de error, catálogo de permisos). Esto cubre solo lo
propio del frontend.

## Stack

React 19, React Router 7 (`BrowserRouter`/`Routes`/`Route` declarativos, sin loaders/actions de
servidor), react-bootstrap 2 + Bootstrap 5.3 (CSS precompilado), Recharts 3, `@dnd-kit/core` +
`@dnd-kit/sortable` (editor visual), Axios. Sin TypeScript, sin Redux/estado global — Context +
hooks custom.

## Rutas (`src/routes/AppRoutes.jsx`)

- Públicas: `/`, `/login`, `/forgot-password`, `/reset-password`, `/403`, `*` (404).
- Privadas: todas anidadas bajo un único `<Route element={<AdminLayout />}>` (mismo sidebar para
  dashboards y administración) — `/app/dashboards/*`, `/admin/*`.
- Protección: `components/auth/RequirePermission.jsx` — sin sesión redirige a `/login`; con
  `permission` y sin ese codename en `user.permissions`, redirige a `/403`. Pásale siempre
  `permission="modulo.accion"` en rutas administrativas; las de `/app/dashboards/:id` dependen del
  control de acceso por-dashboard que resuelve el backend, no de un permiso fijo aquí.

## Cliente HTTP

Tres instancias Axios, todas creadas con el mismo factory `services/httpClient.js`
(`createApiClient(baseURL)`, que ya trae interceptor de Bearer token + refresh automático en 401):
`authApi` (`/api` — auth/users/roles/permissions/branding/audit), `api` (`/api/cartera`), y una
instancia propia dentro de `dashboardLayoutService.js` (`/api/dashboards`). No son duplicación
accidental — reflejan tres prefijos distintos del mismo backend. No crees una cuarta sin usar
`createApiClient`. Detalle en `frontend/src/services/CLAUDE.md`.

No hay interceptor de errores más allá del 401: cada hook/página hace
`.catch(e => setError(e.response?.data?.mensaje || '...'))`. El campo `error` (código) del
contrato de error del backend no se consume en ningún lado del frontend — si necesitas
diferenciar por código de error, sería la primera vez que se hace, confírmalo con el usuario antes
de asumir el patrón.

## Manejo de estado del editor visual

Ver `@.claude/rules/dashboards.md` — grid sin coordenadas, versionado con conflicto 409, Zona
Personal con `DndContext` separado.

## Validación

- `npx vitest run` en verde y `npm run lint` sin warnings nuevos respecto al baseline actual.
- Para cambios visuales (CSS, layout, tema claro/oscuro, editor visual), verifica en navegador —
  no hay Storybook ni pruebas E2E en este repo, Vitest+RTL no capturan regresiones puramente
  visuales.
- Trampas de test (mocks de contexto, `dnd-kit`, accesibilidad) en `@.claude/rules/testing.md`.
