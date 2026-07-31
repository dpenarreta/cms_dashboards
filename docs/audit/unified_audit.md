# Auditoría unificada (Módulo A)

Parte de "Trabajo futuro post-integración con skelleton_base" (ver
`docs/integracion/migration_report.md`, sección "Trabajo futuro completado").

## Qué resuelve

Antes de este módulo existían dos sistemas de auditoría independientes, sin punto de consulta
común:

- `apps.core.AuditLog` — seguridad y administración (login, cambios de usuario/rol/permiso,
  accesos denegados, cambios de branding).
- `cartera.DashboardAuditLog` — cambios de layout del editor visual de dashboards.

Un administrador no podía ver ambos tipos de evento en una sola pantalla, y cada esquema tenía
sus propios nombres de campo (`module`/`target_type` vs. `change_type`/`previous_config`).

## Diseño

### Modelo `AuditEvent` (`backend/apps/audit/models.py`)

Fuente única de auditoría. Campos: `domain`, `action`, `result`, `severity`, `actor` (FK
nullable, `SET_NULL`) + `actor_username` (foto de texto, sobrevive si el usuario se elimina),
`entity_type`/`entity_id`/`entity_name`, `dashboard_id`/`component_id`, `request_id`/`session_id`/
`ip_address`/`user_agent`, `previous_values`/`new_values`/`metadata` (JSON), `message`,
`created_at`.

12 dominios (`AuditEvent.Domain`): `SECURITY`, `AUTHENTICATION`, `USER_MANAGEMENT`,
`ROLE_MANAGEMENT`, `PERMISSION_MANAGEMENT`, `DASHBOARD_ACCESS`, `DASHBOARD_LAYOUT`,
`DASHBOARD_CONFIGURATION`, `DATA_SOURCE`, `EXPORT`, `FILE_UPLOAD`, `SYSTEM_CONFIGURATION`.

### Servicio `log_event` (`backend/apps/audit/services.py`)

Único punto de escritura — ninguna vista ni servicio crea un `AuditEvent` directamente ni sigue
escribiendo en las tablas legacy. Nunca lanza excepción (una falla al auditar no debe interrumpir
la operación de negocio que la originó): captura la excepción y la registra con
`logger.exception`. Severidad por defecto según `result` (`SUCCESS`→`INFO`, `WARNING`→`LOW`,
`FAILED`/`DENIED`→`MEDIUM`), con override explícito disponible. Reutiliza
`apps.core.audit.mask_sensitive_fields`/`request_meta` (ya existentes, no se duplican).

### Migración de todos los call-sites existentes

`apps.core.audit.record_audit_event` se retiró. Todos sus llamadores pasaron a usar
`apps.audit.services.log_event(domain=..., ...)`:

| Archivo | Dominio(s) |
|---|---|
| `apps/authentication/{services,views}.py` | `AUTHENTICATION` |
| `apps/users/services.py` | `USER_MANAGEMENT` (asignar permisos → `PERMISSION_MANAGEMENT`, decisión deliberada: es semánticamente gestión de permisos, no de usuarios) |
| `apps/roles/views.py` | `ROLE_MANAGEMENT` |
| `apps/branding/views.py` | `SYSTEM_CONFIGURATION` |
| `apps/permissions/permissions.py` (`HasModulePermission`, acceso denegado) | `SECURITY` |
| `cartera/services/dashboard_layout.py` (`aplicar_layout`/`restablecer_layout`) | `DASHBOARD_LAYOUT` (cambios por componente) / `DASHBOARD_CONFIGURATION` (restablecer) |

`apps.core.AuditLog` y `cartera.DashboardAuditLog` **se conservan sin cambios** (tabla y datos
históricos intactos) — solo dejan de recibir filas nuevas. `apps/core/audit.py` documenta esto en
su docstring.

`cartera/dashboard_views.py::DashboardVersionsView` pasó de consultar `DashboardAuditLog` a
consultar `AuditEvent` (mismo shape de respuesta que ya consumía el frontend:
`component_id`/`change_type`/`changed_by`/`changed_at`/`version` — mapeados desde
`action`/`metadata.changed_by_label`/`created_at`/`metadata.version`).

### Migración de datos históricos (no destructiva)

`apps/audit/migrations/0002_migrar_historico_legacy.py` copia las filas existentes de
`apps.core.AuditLog` y `cartera.DashboardAuditLog` a `AuditEvent`, con
`metadata.source_audit_system` = `"core_auditlog_legacy"` / `"dashboard_layout_legacy"` y
`metadata.legacy_id` apuntando a la fila de origen, para trazabilidad. Las tablas legacy **no se
tocan** (ni se borran filas ni se altera su esquema). La migración es reversible sin afectarlas:
el rollback solo borra los `AuditEvent` que ella misma creó (identificados por
`metadata.source_audit_system`).

Se preserva `created_at`/`changed_at` original vía `AuditEvent.objects.filter(pk=...).update(...)`
— `auto_now_add` bloquea fijar la fecha directamente en `.create()`, pero `.update()` la ignora,
permitiendo conservar la fecha histórica real en vez de la fecha de ejecución de la migración
(verificado explícitamente en el entorno de desarrollo).

**Corrección durante la implementación**: la primera versión de la migración no calculaba
`severity` para las filas migradas (quedaban todas en `INFO` por defecto, incluyendo login
fallidos). Se corrigió agregando el mismo mapeo resultado→severidad que usa `log_event`.

### Permisos

Se reutilizan los códigos **ya existentes en el catálogo** — `auditoria.ver`,
`auditoria.ver_detalle`, `auditoria.exportar` (antes huérfanos, sin ningún endpoint que los
consumiera) — en vez de introducir nombres nuevos, mismo criterio ya aplicado con los permisos
`dashboard.*` en la integración anterior.

### API (`GET/POST /api/audit/`)

- `GET /api/audit/` — lista paginada, filtros: `date_from`, `date_to`, `domain`, `action`
  (`icontains`), `result`, `severity`, `actor` (id o username), `dashboard_id`, `component_id`,
  `entity_type`, `entity_id`, `ip_address`, `q` (texto libre sobre acción/mensaje/entidad/actor).
  Requiere `auditoria.ver`.
- `GET /api/audit/<id>/` — detalle. Requiere `auditoria.ver`; oculta
  `previous_values`/`new_values`/`metadata` si el usuario no tiene además `auditoria.ver_detalle`
  (`AuditEventDetailSerializer.to_representation`).
- `GET /api/audit/export/` — CSV (tope 5000 filas), requiere `auditoria.exportar`, reutiliza
  `cartera.services.export_service.generar_csv` (misma sanitización anti-inyección de fórmulas
  que ya usan las exportaciones de cartera).

### Frontend

`frontend/src/pages/administration/audit/AuditListPage.jsx` — tabla con filtros, paginación
`page`/`next`/`previous` (mismo patrón que `UsersListPage`), modal de detalle (valores
anteriores/nuevos/metadata, solo si el usuario tiene `auditoria.ver_detalle`), botón de
exportación (solo si tiene `auditoria.exportar`, descarga vía blob + `Authorization` header —
un `<a href>` directo no funciona porque el endpoint exige token). Ítem "Auditoría" en
`config/adminMenu.js`, ruta `/admin/audit`.

Columnas mínimas de la tabla (sección 4.5 del prompt): Fecha y hora, Dominio, Acción, Resultado,
Usuario, Entidad, Descripción, Dirección IP, Detalle — la columna "Descripción" (`message`) se
había omitido en la primera versión; se agregó tras releer la lista de columnas mínimas exigida.

## Pruebas

- `backend/apps/audit/tests.py` — 14 pruebas (`log_event` nunca lanza, severidad por defecto y
  override, enmascarado de valores sensibles, actor anónimo, permisos de list/retrieve/export).
- `backend/cartera/tests/test_dashboard_layout.py` — actualizado para afirmar contra `AuditEvent`
  (antes afirmaba contra `DashboardAuditLog`, que ya no recibe escrituras).
- `backend/apps/roles/tests.py` — 2 pruebas actualizadas (mismo motivo).
- `frontend/src/tests/AuditListPage.test.jsx` — 7 pruebas (listado, filtros, permisos, detalle).
- Suite completa verificada en verde: 156 pruebas backend, 194 pruebas frontend.
- Verificación manual en Chrome: listado con datos migrados reales, filtro por dominio, modal de
  detalle, exportación CSV, sin errores de consola.
