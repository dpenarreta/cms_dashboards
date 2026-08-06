# pages/

Hereda `../../CLAUDE.md`. Una página por ruta de `routes/AppRoutes.jsx` — no pongas lógica de
negocio en una página, delega a `hooks/` o `services/`.

## Responsabilidad por subcarpeta

- `administration/{users,roles,permissions,settings,audit}/` — patrón lista + formulario por
  dominio administrativo (ej. `UsersListPage.jsx` + `UserFormPage.jsx`). `permissions/` es de solo
  lectura (catálogo, sin formulario). Cada página administrativa asume que ya pasó por
  `RequirePermission` en la ruta — no revalides el permiso de nuevo ahí salvo para mostrar/ocultar
  un botón puntual dentro de la misma página (ej. patrón usado en `UsersListPage` para el botón de
  restablecer contraseña, gateado por `user.permissions.includes('usuarios.restablecer_password')`).
- `authentication/` — `LoginPage`, `ForgotPasswordPage`, `ResetPasswordPage`: públicas, fuera de
  `AdminLayout`.
- `dashboards/` — `DashboardsListPage` (listado/creación), `DashboardAreaPage` (vista/edición de
  un dashboard real — el editor visual vive acá, ver `components/dashboard-editor/CLAUDE.md`
  heredado de `dashboards.md`), `DashboardHistoricoPage`.
- `errors/` — `ForbiddenPage` (403), `NotFoundPage` (404) — destino de `RequirePermission` y de la
  ruta catch-all.
- `public/` — `LandingPage`: pública, sin sesión.

## Reglas

- Toda página nueva bajo `/admin/*` necesita su entrada en `routes/AppRoutes.jsx` envuelta en
  `<RequirePermission permission="modulo.accion">` — el permiso debe existir ya en el catálogo
  backend (`apps/permissions/catalog.py`), no lo inventes solo en frontend.
- Errores de servicio se muestran con `<Alert variant="danger">{mensaje}</Alert>`, leyendo
  `e.response?.data?.mensaje` — mismo patrón en todas las páginas existentes, no introduzcas un
  mecanismo de notificación distinto (toast, etc.) sin confirmarlo.
