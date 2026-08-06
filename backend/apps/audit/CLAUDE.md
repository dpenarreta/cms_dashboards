# Módulo: audit

Hereda `../../CLAUDE.md` y `@.claude/rules/security.md`.

## Responsabilidad

Auditoría unificada — único punto de escritura y consulta para todos los eventos del sistema
(seguridad, gestión de usuarios/roles/permisos, layout de dashboards, branding). Reemplaza a los
dos sistemas legacy `apps.core.AuditLog` y `cartera.DashboardAuditLog`, que se conservan intactos
solo como histórico (ver `backend/apps/core/CLAUDE.md`).

## Estructura

- `models.py` — `AuditEvent`: `domain` (12 valores: `SECURITY`, `AUTHENTICATION`,
  `USER_MANAGEMENT`, `ROLE_MANAGEMENT`, `PERMISSION_MANAGEMENT`, `DASHBOARD_ACCESS`,
  `DASHBOARD_LAYOUT`, `DASHBOARD_CONFIGURATION`, `DATA_SOURCE`, `EXPORT`, `FILE_UPLOAD`,
  `SYSTEM_CONFIGURATION`), `action` (string libre, no hay enum cerrado), `result`, `severity`,
  `actor` (FK nullable) + `actor_username` (foto de texto, sobrevive si se borra el usuario),
  `entity_type`/`entity_id`/`entity_name`, `previous_values`/`new_values`/`metadata` (JSON).
- `services.py` — `log_event(domain=..., action=..., actor=None, ...)`: único punto de escritura.

## Reglas

- IMPORTANT: `log_event` nunca lanza excepción — captura cualquier fallo y lo registra con
  `logger.exception`, para que una falla de auditoría no interrumpa la operación de negocio que la
  originó. Si lo llamas, no lo envuelvas en `try/except` adicional.
- Severidad por defecto según `result` (`SUCCESS`→`INFO`, `WARNING`→`LOW`, `FAILED`/`DENIED`→
  `MEDIUM`) — pásala explícita solo si el evento amerita otra.
- Reutiliza `apps.core.audit.mask_sensitive_fields`/`request_meta` para `previous_values`/
  `new_values`/metadatos de request — no dupliques ese enmascarado.
- Un evento nuevo con `action` en texto libre: sigue la convención `DOMINIO_VERBO` en mayúsculas
  (ej. `USER_PASSWORD_RESET_BY_ADMIN`) para que sea buscable/filtrable en `GET /api/audit/`.

## Permisos

`auditoria.ver` (listar/detalle básico), `auditoria.ver_detalle` (además,
`previous_values`/`new_values`/`metadata` — sin este permiso, `AuditEventDetailSerializer` los
oculta), `auditoria.exportar` (CSV, tope 5000 filas).

## Evita

- No escribas directo en `apps.core.AuditLog` ni `cartera.DashboardAuditLog` desde código nuevo —
  ambos dejaron de recibir filas nuevas, solo conservan histórico migrado
  (`apps/audit/migrations/0002_migrar_historico_legacy.py`).
