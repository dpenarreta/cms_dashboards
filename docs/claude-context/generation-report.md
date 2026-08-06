# Informe de generación — jerarquía de archivos CLAUDE.md

Fecha: 2026-08-06. Alcance: repositorio completo `cms_dashboards` (backend Django + frontend
React, sin monorepo tooling, sin CI/Docker). Ver `context-map.md` para la matriz completa de
carpetas evaluadas.

## Archivos creados

| Archivo | Líneas | Nivel | Responsabilidad | Estado |
|---|---|---|---|---|
| `CLAUDE.md` | 100 | Proyecto | Comandos, arquitectura, contrato de error, permisos | Creado |
| `CLAUDE.local.md` | 24 | Local | Entorno de esta máquina (SQL Server local, venv, Chrome) | Creado |
| `docs/claude-context/proposed-global-CLAUDE.md` | — | Global (propuesta) | Idioma, SO, shell | Creado |
| `backend/CLAUDE.md` | 49 | Aplicación | Capas, DB, migraciones, errores/permisos | Creado |
| `backend/cartera/CLAUDE.md` | 65 | Módulo | Motor de cartera, contrato de error global, permisos legacy | Creado |
| `backend/apps/core/CLAUDE.md` | 27 | Módulo | `BaseModel`, `AuditLog` legacy congelado | Creado |
| `backend/apps/permissions/CLAUDE.md` | 39 | Módulo | Catálogo cerrado de permisos | Creado |
| `backend/apps/authentication/CLAUDE.md` | 44 | Módulo | JWT, sesiones, recuperación de contraseña | Creado |
| `backend/apps/users/CLAUDE.md` | 39 | Módulo | CRUD de usuarios, último admin activo | Creado |
| `backend/apps/roles/CLAUDE.md` | 39 | Módulo | Roles = `Group`, borrado sin protección | Creado |
| `backend/apps/branding/CLAUDE.md` | 38 | Módulo | Identidad institucional singleton | Creado |
| `backend/apps/audit/CLAUDE.md` | 44 | Módulo | Auditoría unificada, `log_event` | Creado |
| `frontend/CLAUDE.md` | 49 | Aplicación | Rutas, wrappers HTTP, validación | Creado |
| `frontend/src/components/CLAUDE.md` | 35 | Módulo | Responsabilidad por subcarpeta, dos `DndContext` | Creado |
| `frontend/src/pages/CLAUDE.md` | 30 | Módulo | Patrón lista+formulario, `RequirePermission` | Creado |
| `frontend/src/services/CLAUDE.md` | 38 | Módulo | 3 wrappers Axios, por qué no son 1 | Creado |
| `frontend/src/hooks/CLAUDE.md` | 37 | Módulo | Inventario, advertencia `usePermisos` stub | Creado |
| `frontend/src/context/CLAUDE.md` | 32 | Módulo | `AuthContext`/`ThemeContext`, trampa de Bootstrap | Creado |
| `tests/CLAUDE.md` | 23 | Módulo | Gherkin no ejecutable, trazabilidad | Creado |
| `docs/CLAUDE.md` | 27 | Módulo | Qué documento actualizar y cuándo | Creado |
| `.claude/rules/security.md` | 48 | Compartido (import) | Hash, JWT, upload, enmascarado | Creado |
| `.claude/rules/testing.md` | 40 | Compartido (import) | Comandos + trampas reales de test | Creado |
| `.claude/rules/dashboards.md` | 59 | Compartido (import) | Grid, versionado, Zona Personal, paginación | Creado |

Total: 19 `CLAUDE.md` + 1 `CLAUDE.local.md` + 1 propuesta global + 3 reglas compartidas = 24
archivos, 777 líneas en archivos `CLAUDE*.md` (ninguno supera 100 líneas; el raíz es el más largo
con 100).

## Archivos actualizados

- `.gitignore` — se agregó `CLAUDE.local.md` (no estaba ignorado; ahora sí, verificado con
  `git check-ignore -v CLAUDE.local.md`).

## Carpetas evaluadas y omitidas (con motivo)

Ver tabla completa en `context-map.md`. Resumen de omisiones:
- `backend/config/` — settings/urls/wsgi sin lógica editable con frecuencia; cubierto en
  `backend/CLAUDE.md`.
- `frontend/src/utils/`, `frontend/src/config/` — nombres autoexplicativos, sin trampas no
  obvias que documentar.
- `frontend/src/tests/`, `frontend/src/assets/`, `frontend/public/` — sin reglas propias más
  allá de lo ya cubierto en `.claude/rules/testing.md` o sin lógica.
- `scripts/`, `infrastructure/`, `.github/workflows/` — no existen en este repo, no se inventaron.
- Carpetas generadas (`node_modules/`, `.venv/`, `__pycache__/`, `media/`, `dist/`, `coverage/`) —
  excluidas por regla explícita del prompt de generación.

## Reglas compartidas vía `@`

Se crearon 3 archivos en `.claude/rules/` porque su contenido aplicaba a más de 2 módulos y
duplicarlo en cada `CLAUDE.md` hubiera excedido el objetivo de longitud (40-120 líneas):
- `security.md` — referenciado desde raíz, `backend/CLAUDE.md`,
  `backend/apps/{authentication,users,permissions,audit}/CLAUDE.md`, `backend/cartera/CLAUDE.md`.
- `testing.md` — referenciado desde raíz, `backend/CLAUDE.md`, `frontend/CLAUDE.md`.
- `dashboards.md` — referenciado desde `backend/cartera/CLAUDE.md` y
  `frontend/src/components/CLAUDE.md` (regla que cruza backend/frontend, no pertenece a ninguno
  de los dos en exclusiva).

## Reglas globales detectadas (evidencia directa en la sesión)

Idioma de respuesta (español), sistema operativo (Windows 11), shell (PowerShell + Git Bash). Se
dejaron como propuesta en `docs/claude-context/proposed-global-CLAUDE.md` en vez de escribir
directo en `~/.claude/CLAUDE.md`, porque ese archivo afecta a todos los proyectos del usuario, no
solo a este repositorio — se prefirió dejar la decisión final en manos del usuario. Campos típicos
de un `CLAUDE.md` global (editor, gestor de paquetes preferido fuera de este proyecto, convención
de commits personal) se dejaron fuera explícitamente por falta de evidencia — no se inventaron.

## Reglas del proyecto detectadas (fuente: código + `docs/integracion/decisions.md`)

Contrato de error único (`CarteraError`), catálogo cerrado de permisos con formato
`modulo.accion`, `IsAuthenticated` global por defecto, Django `TestCase` (no pytest), sin
TypeScript/typecheck, 3 wrappers Axios sobre el mismo factory, grid del editor visual sin
coordenadas absolutas, migraciones con datos reales (nunca editar una aplicada).

## Módulos con contexto específico

Backend: `cartera` (el más extenso, motor original), `authentication`, `users`, `roles`,
`branding`, `permissions`, `audit`, `core`. Frontend: `components`, `pages`, `services`, `hooks`,
`context`. Todos con reglas propias no derivables trivialmente del código (ver columna "Motivo"
en `context-map.md`).

## Contradicciones encontradas y resueltas

1. **Convención de commits inventada inicialmente** — el primer borrador de `CLAUDE.md` raíz
   afirmaba "commits en español, imperativo", pero `git log` real muestra solo 3 commits con
   estilo mixto (español/inglés, descriptivo, no imperativo corto). Se corrigió para reflejar la
   ausencia de una convención estrictamente observada, en vez de prescribir una no evidenciada.
2. **Rama actual vs. rama principal** — el repo está actualmente en
   `feature/post-integration-future-work` (con cambios sin commitear ajenos a esta tarea, no
   tocados), pero `origin/HEAD` apunta a `main`. El `CLAUDE.md` raíz declara `main` como rama
   principal (correcto: es la rama por defecto del remoto), sin asumir que el checkout actual
   sea siempre `main`.
3. Sin otras contradicciones (gestor de paquetes, indentación, framework de test) detectadas
   entre niveles — el proyecto usa consistentemente un único gestor por lenguaje (`npm`/`pip`) y
   un único framework de test por lado (`TestCase`/Vitest).

## Comandos verificados contra configuración real

- `npm install|run dev|run build|run preview|test|run lint` — confirmados en
  `frontend/package.json::scripts`.
- `pip install -r requirements.txt`, `python manage.py migrate|runserver|test|makemigrations|
  shell|clean_temp_uploads` — confirmados en `backend/requirements.txt` y
  `backend/cartera/management/commands/clean_temp_uploads.py`.
- No se documentó ningún comando de typecheck (no existe `tsconfig.json`) ni de lint Python (no
  existe `ruff.toml`/`.flake8`/`pyproject.toml` con esa config) — confirmado por búsqueda directa
  en el repo, no se inventó ninguno.

## Riesgos pendientes (no corregidos en esta tarea — es generación de contexto, no de código)

- `RoleViewSet.perform_destroy` (`backend/apps/roles/views.py`) permite borrar el rol
  `ADMINISTRADOR_GENERAL` sin ninguna protección — documentado como trampa en
  `backend/apps/roles/CLAUDE.md`, no se modificó el código (fuera del alcance de esta tarea).
- Working tree tiene cambios sin commitear en `backend/apps/{permissions,users}/*` ajenos a esta
  tarea (trabajo previo de la sesión) — no se tocaron ni se incluyeron en ningún `CLAUDE.md`.
- La propuesta de contexto global no fue copiada a `~/.claude/CLAUDE.md` — queda pendiente de que
  el usuario decida copiarla.
