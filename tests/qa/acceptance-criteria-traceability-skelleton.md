# Matriz de trazabilidad — Integración de skelleton_base

Fuente: `tests/qa/skelleton_base_integration.feature`.

Misma convención que las matrices anteriores: `Aprobado` solo si la prueba indicada se ejecutó y
pasó en esta sesión. `No aplica (diferido)` = decisión explícita documentada en
`docs/integracion/decisions.md`, no un olvido.

| ID | Criterio | Prueba(s) que lo cubren | Automatizado | Estado |
|---|---|---|---|---|
| AC-INT-001 | cms_dashboards como repositorio principal | `git log`/`git status`/`git branch --show-current` en cada fase; todo el código vive en `C:\...\cms_dashboards`, rama `feature/integracion-skelleton-base` | No (verificación de proceso, no de código) | Verificado manualmente |
| AC-INT-002 | Informe de diferencias generado | `docs/integracion/skelleton_base_comparison.md`, `docs/integracion/file_migration_matrix.md` | No (documentación) | Aprobado |
| AC-INT-003 | Conservar la landing pública | — | No aplica | **Diferido por decisión explícita** (`docs/integracion/decisions.md`, respuesta del usuario a la pregunta de alcance de landing): ni `cms_dashboards` ni `skelleton_base` tenían una landing real antes de la integración; se decidió omitirla en esta ronda de fases en vez de construir una nueva sin que se pidiera |
| AC-INT-004 | Login autentica, genera tokens seguros, sin contraseñas en texto plano | `apps/authentication/tests.py::LoginViewTests` (login válido/inválido/email/bloqueo), `PASSWORD_HASHERS` con Argon2 primero (`config/settings.py`) | Sí | Aprobado |
| AC-INT-005 | Proteger un dashboard sin permiso | Backend: `cartera/tests/test_dashboard_authorization.py::test_autenticado_sin_permiso_dashboard_view_devuelve_403`. Frontend: `RequirePermission.test.jsx` ("autenticado pero sin el permiso requerido, redirige a /403"), `ForbiddenPage.jsx` muestra el mensaje | Sí | Aprobado |
| AC-INT-006 | Autorizar un dashboard con permiso | `test_autenticado_con_permiso_dashboard_view_pasa_la_verificacion`, `DashboardsAuthorizedViewTests::test_usuario_con_dashboard_view_ve_cartera` (la API filtra las fuentes por permiso, no el frontend) | Sí | Aprobado |
| AC-INT-007 | Administrador general ve todo | `test_administrador_general_ve_el_dashboard_sin_asignacion_individual`, `test_administrador_general_ve_todos_los_dashboards_autorizados`, `test_rol_administrador_general_tiene_el_catalogo_completo` (incluye `configuracion.ver`/`configuracion.editar`) | Sí | Aprobado |
| AC-INT-008 | Menú según permisos | `AdminSidebar.test.jsx` ("solo lista los módulos administrativos que el usuario tiene permiso de ver") | Sí | Aprobado |
| AC-INT-009 | Conservar el dashboard de cartera (KPIs/gráficos/filtros/matrices) | Las 77 pruebas originales de `cartera/tests/test_api.py` (con autenticación agregada en `setUp`, sin tocar sus aserciones de negocio) siguen en verde | Sí | Aprobado |
| AC-INT-010 | Evitar duplicidad de usuarios | Un único `AUTH_USER_MODEL = 'users.User'`; roles = `Group`; permisos = `Permission` — `docs/integracion/decisions.md` #2/#3/#4 | Parcial (verificación de diseño; no hay "prueba" de ausencia de un segundo modelo) | Aprobado |
| AC-INT-011 | 401 sin token | `test_dashboard_authorization.py::ProteccionEndpointsCarteraTests::test_sin_token_devuelve_401`, `DashboardsAuthorizedViewTests::test_sin_token_devuelve_401` | Sí | Aprobado |
| AC-INT-012 | 403 sin permiso | `test_autenticado_sin_permiso_dashboard_view_devuelve_403` | Sí | Aprobado |
| AC-INT-013 | Auditoría de cambios administrativos | `apps/roles/tests.py::test_modificar_permisos_de_un_rol_registra_auditoria`, `test_crear_rol_registra_auditoria` | Sí | Aprobado |
| AC-INT-014 | Única configuración institucional | `ThemeContext.test.jsx`; verificado manualmente que `/login` (sin sesión) y el panel autenticado leen la misma `GET /api/branding/current`. La cláusula "la landing... debe utilizarla" no aplica por AC-INT-003 | Sí (parcial, ver nota) | Aprobado con nota (landing no aplica) |
| AC-INT-015 | Pruebas después de cada fase | Cada fase (2, 3, 4, 5, 6, 7) se cerró ejecutando la suite completa (Django + Vitest) antes de continuar — ver el detalle por fase en `docs/integracion/integration_plan.md` | Sí (proceso, no un test unitario propio) | Aprobado |

## Notas

- **AC-INT-003/AC-INT-014 (landing)**: el prompt original de integración asume que
  `cms_dashboards` ya tenía una landing pública ("conservarla"), pero no era el caso —
  confirmado leyendo `frontend/src/App.jsx` antes de empezar (renderizaba directo el dashboard,
  sin rutas). Se le preguntó al usuario cómo resolver esta discrepancia y se decidió omitir la
  landing en esta ronda de fases; la aplicación entra directo a `/login`. Documentado también en
  `docs/integracion/decisions.md`.
- **AC-INT-010**: no existe una prueba automatizada que pruebe una negativa ("no existe un
  segundo modelo de usuario") — se verifica por diseño (una sola entrada en `AUTH_USER_MODEL`,
  imposible tener dos modelos de usuario simultáneos en Django).
