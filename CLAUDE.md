# Dashboard de Cartera (cms_dashboards)

## Propósito

Carga un Excel de cartera de clientes, lo valida/mapea/procesa y genera un dashboard ejecutivo
(KPIs, gráficos, filtros, tabla, exportación, drill-down), con un editor visual de layout y un
panel de administración (usuarios/roles/permisos/auditoría/identidad institucional). Backend
Django + frontend React, sin monorepo tooling (dos proyectos independientes: `backend/`,
`frontend/`).

## Comandos

Backend (`cd backend`, con `.venv` activo):
- Instalar: `pip install -r requirements.txt`
- Migrar: `python manage.py migrate`
- Desarrollo: `python manage.py runserver 8000`
- Test (todo): `python manage.py test` — Test (una app): `python manage.py test apps.users`
- No hay lint/formatter configurado para Python en este repo (no inventes `ruff`/`black`/`flake8`).

Frontend (`cd frontend`):
- Instalar: `npm install`
- Desarrollo: `npm run dev` (puerto 5173, proxy `/api` → `http://localhost:8000`)
- Build: `npm run build` — Preview: `npm run preview`
- Test: `npm test` (= `vitest run`) — Lint: `npm run lint` (oxlint)
- No hay `tsconfig.json`: el proyecto es JavaScript puro, no hay comando de typecheck.

Detalle y trampas de pruebas: `@.claude/rules/testing.md`.

## Arquitectura

- **Backend**: Django 5 + DRF, patrón vistas → servicios → modelos. La lógica de negocio vive en
  `services/`, no en vistas ni serializers.
- **Contrato de error único**: `cartera.exceptions.CarteraError` + `cartera_exception_handler` es
  el `EXCEPTION_HANDLER` global (`config/settings.py`) — aplica a **toda** la API, no solo a
  `cartera`. Un error de negocio en cualquier app se lanza como `CarteraError(mensaje,
  codigo=..., detalles=...)` y responde `{"error", "mensaje", "detalles"}` con 400.
- **Permisos**: catálogo cerrado único en `apps.permissions.catalog.PERMISSION_CATALOG` (formato
  `modulo.accion`, ej. `usuarios.ver`). Un superusuario recibe automáticamente el catálogo
  completo — nunca compares contra el nombre de un rol para decidir acceso, siempre contra el
  codename del permiso.
- **Frontend**: sin Redux/estado global — Context (`AuthContext`, `ThemeContext`) + hooks por
  página/hook custom. Tres wrappers Axios distintos por prefijo de API (`/api`, `/api/cartera`,
  `/api/dashboards`), todos construidos con el mismo factory (`services/httpClient.js`) — no es
  duplicación accidental, ver `frontend/src/services/CLAUDE.md`.

## Estructura

- `backend/cartera/` — app original: carga/cálculo de cartera, editor visual, contrato de error
  global. Ver `backend/cartera/CLAUDE.md`.
- `backend/apps/{core,permissions,authentication,users,roles,branding,audit}/` — integración
  "skelleton_base" (auth, usuarios, roles, permisos, branding, auditoría unificada). Cada una
  tiene su propio `CLAUDE.md`.
- `frontend/src/` — `components/`, `pages/`, `services/`, `hooks/`, `context/`: cada carpeta
  relevante tiene su propio `CLAUDE.md`.
- `tests/qa/` — criterios de aceptación en Gherkin (documentación, no se ejecutan como suite).
- `docs/` — decisiones de arquitectura (`integracion/decisions.md`) y features post-integración.

## Reglas críticas

- IMPORTANT: nunca edites una migración ya mergeada (`backend/cartera/migrations/` y
  `backend/apps/*/migrations/` tienen migraciones de datos reales — seeds, backfills). Crea una
  migración nueva.
- YOU MUST validar permisos en el backend (`require_permission`) en toda vista nueva que mute
  datos — ocultar un botón en el frontend nunca es la protección real. Detalle en
  `@.claude/rules/security.md`.
- No dupliques sistemas: hay un único catálogo de permisos, un único contrato de error, un único
  punto de escritura de auditoría (`apps.audit.services.log_event`). Antes de crear algo nuevo con
  ese propósito, busca si ya existe.

## Entorno

- `DATABASE` vía `DB_ENGINE` (`mssql` por defecto, requiere SQL Server + ODBC Driver 17; `sqlite`
  para desarrollo sin SQL Server).
- `JWT_SECRET_KEY`, `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS`: firma
  y vigencia de tokens.
- `EMAIL_*`, `FRONTEND_URL`, `PASSWORD_RESET_*`: recuperación de contraseña (backend de consola
  por defecto, nunca envía correo real sin `EMAIL_BACKEND` explícito).
- `CORS_ALLOWED_ORIGINS`, `UPLOAD_MAX_SIZE_BYTES`: ver `backend/.env.example` para la lista
  completa de nombres (sin valores).
- Requiere SQL Server accesible antes de correr migraciones o pruebas backend (salvo
  `DB_ENGINE=sqlite`).

## Validación

Antes de dar una tarea por terminada:
- Backend: `python manage.py test` (o el subset de la app tocada) en verde.
- Frontend: `npx vitest run` en verde y `npm run lint` sin warnings nuevos respecto al baseline
  (revisa la salida actual del comando, no asumas cero warnings — hay warnings preexistentes de
  `react-refresh` que no bloquean).
- Para cambios visuales, verifica en navegador (no solo con tests) — no hay Storybook ni pruebas
  E2E automatizadas en este repo.

## Git

- Rama principal: `main` (`origin/HEAD` apunta ahí). Ramas de trabajo observadas:
  `feature/<nombre-descriptivo>`.
- El historial existente (3 commits) no fija una convención estricta de mensajes (mezcla español/
  inglés, mensajes descriptivos largos, no imperativos cortos) — no asumas un formato único; si el
  usuario no indica lo contrario, preferí un resumen claro del "qué" y el "por qué" del cambio.
- No hay hooks de pre-commit configurados. La CI (`.github/workflows/ci.yml`) corre en cada push a
  `main`/`feature/**` y en cada PR hacia `main`: pruebas de backend y frontend, lint, verificación
  de migraciones faltantes (`makemigrations --check`) y `check --deploy`.
- IMPORTANT: la CI ejecuta el backend con `DB_ENGINE=sqlite` y `DEBUG=False`. Una prueba que
  dependa de SQL Server (colación case-insensitive, validación de `max_length` en la base) o que
  asuma `DEBUG=True` pasa en tu máquina y falla en CI — ya ocurrió con ambas cosas.
