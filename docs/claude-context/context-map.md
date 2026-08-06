# Mapa de contexto — archivos CLAUDE.md

Generado por inspección directa del repositorio (sin CI/Docker/Makefile — no aplican). Motor de
verdad para comandos: `frontend/package.json`, `backend/requirements.txt`,
`backend/config/settings.py`, `.oxlintrc.json`, `vite.config.js`, `README.md`.

| Carpeta | Responsabilidad | ¿Requiere CLAUDE.md? | Motivo | Contexto heredado | Reglas locales |
|---|---|---|---|---|---|
| `~/.claude/CLAUDE.md` | Preferencias del usuario en todos sus proyectos | Propuesta | No editable con certeza de alcance global — se deja como propuesta | — | Idioma, SO, shell, edición |
| `/` | Proyecto general | Sí | Comandos, arquitectura, stack | Global | Comandos exactos, contrato de error, permisos, entorno |
| `/CLAUDE.local.md` | Config de esta máquina | Sí | DB local, venv, navegador de pruebas | Proyecto | SQL Server local, rutas `.venv` |
| `/backend` | API Django (MVT) | Sí | Comandos propios (`manage.py`), capas | Proyecto | Test runner, apps instaladas, DB |
| `/backend/config` | settings/urls/wsgi | No | Sin lógica propia editable con frecuencia | Backend | — (cubierto en backend/CLAUDE.md) |
| `/backend/cartera` | Motor original: carga Excel, cálculo cartera, editor visual, contrato de error global | Sí | Reglas de cálculo, migraciones con datos reales, permisos legacy | Backend | Modelos, `CarteraError`, permisos, migraciones, upload |
| `/backend/apps/core` | `BaseModel` + `AuditLog` legacy congelado + enmascarado | Sí | Trampa: no escribir en `AuditLog` directo | Backend | `log_event` es el único punto de escritura |
| `/backend/apps/permissions` | Catálogo cerrado de permisos, única fuente de verdad | Sí | Formato de codename, `require_permission` vs `IsSuperuser` | Backend | Catálogo cerrado, superusuario implícito |
| `/backend/apps/authentication` | JWT, sesiones revocables, fuerza bruta | Sí | Seguridad crítica | Backend + `.claude/rules/security.md` | Hash, tokens, sesión, throttle |
| `/backend/apps/users` | CRUD de usuarios, protección último admin | Sí | Reglas de negocio no obvias | Backend | Último admin activo, `must_change_password` |
| `/backend/apps/roles` | Roles = `Group` nativo | Sí | Trampa: sin protección al borrar rol admin | Backend | Wrapper sobre `Group`, sin modelo propio |
| `/backend/apps/branding` | Identidad institucional, singleton | Sí | Singleton forzado, endpoint público | Backend | `get_solo()`, nunca instanciar directo |
| `/backend/apps/audit` | Auditoría unificada, fuente única | Sí | `log_event` nunca lanza, dominios cerrados | Backend | 12 dominios, migración de legacy |
| `/frontend` | App React 19 + Vite | Sí | Comandos, rutas, wrappers HTTP | Proyecto | `npm run dev/build/test/lint`, sin typecheck |
| `/frontend/src/components` | UI por dominio (13 subcarpetas) | Sí | Convención de dos `DndContext`, grid sin coordenadas | Frontend + `.claude/rules/dashboards.md` | Responsabilidad por subcarpeta |
| `/frontend/src/pages` | Páginas por ruta | Sí | Patrón lista+formulario, `RequirePermission` | Frontend | Estructura por subcarpeta |
| `/frontend/src/services` | Clientes HTTP | Sí | 3 wrappers axios distintos (no es duplicación accidental) | Frontend | Cuál wrapper usar según prefijo |
| `/frontend/src/hooks` | Lógica reutilizable | Sí | Trampa: `usePermisos` es un stub que concede todo | Frontend | Lista de hooks + advertencia |
| `/frontend/src/context` | `AuthContext`, `ThemeContext` | Sí | Bootstrap precompilado no lee `--bs-primary` | Frontend | Override de variables Bootstrap |
| `/frontend/src/utils` | Formato, colores, contraste | No | Nombres autoexplicativos, sin trampas | Frontend | — |
| `/frontend/src/config` | Menú admin, contenido landing | No | Arrays estáticos simples | Frontend | — |
| `/frontend/src/tests` | Setup Vitest | No | Cubierto por `.claude/rules/testing.md` | Frontend | — |
| `/frontend/src/assets`, `/frontend/public` | Estáticos | No | Sin lógica | Frontend | — |
| `/tests` | Criterios de aceptación Gherkin (no automatizados) | Sí | Relación con pruebas reales no es obvia | Proyecto | Qué son, qué no ejecutan |
| `/docs` | Documentación técnica y decisiones (ADR) | Sí | Cuándo actualizar cada documento | Proyecto | `decisions.md`, sincronía con README |
| `.claude/rules/security.md` | Reglas de seguridad compartidas | Sí (import) | Evita repetir en 4 apps de auth/datos | — | Hash, JWT, upload, enmascarado |
| `.claude/rules/testing.md` | Convenciones de pruebas compartidas | Sí (import) | Gotchas reales de esta sesión (dnd-kit, mocks) | — | Comandos y trampas de test |
| `.claude/rules/dashboards.md` | Convenciones del editor visual (back+front) | Sí (import) | Compartidas entre `cartera` y `dashboard-editor` | — | Grid, versionado, paginación |

## Carpetas omitidas explícitamente

No existen en este repo (no se inventan): `scripts/`, `infrastructure/`, `.github/workflows/`,
`docker-compose.yml`, `Makefile`, `tsconfig.json`. `backend/media/`, `backend/apps/__pycache__/`,
`frontend/node_modules/` se excluyen por ser generadas/ignoradas.
