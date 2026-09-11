# Módulo: core

Hereda `../../CLAUDE.md`.

## Responsabilidad

Infraestructura transversal mínima: `BaseModel` abstracto y utilidades de auditoría reutilizadas
por `apps.audit`. No es un módulo de negocio — no le agregues lógica específica de un dominio.

## Estructura

- `models.py` — `BaseModel(models.Model)` abstracto: **solo** `created_at`/`updated_at`
  (`auto_now_add`/`auto_now`). No tiene `uuid` ni soft-delete — no asumas que lo tiene. Lo heredan
  `apps.authentication`, `apps.branding` (`SiteTheme`) y `apps.users`. `cartera/models.py` **no**
  hereda de acá — sus modelos son `models.Model` planos con timestamps ad-hoc propios.
- `audit.py` — `mask_sensitive_fields(valores)` (enmascara claves con `password`/`token`/
  `secret`/`refresh`/`access`/`key`/`authorization`/`credential`), `request_meta(request)` (IP +
  user-agent, tolerante a `X-Forwarded-For`).
- `password.py` — `validar_fortaleza(password, usuario=None)` y `campo_password(**kwargs)`: punto
  único donde se invoca `validate_password` con los validadores de `settings`. Lo usan las cuatro
  rutas que fijan una contraseña.
- `imagenes.py` — `CampoImagenSegura` (campo de DRF) y `validar_extension_y_firma(nombre, cabecera)`:
  restringen las imágenes subidas a PNG/JPEG/WebP comprobando la firma binaria **antes** de que
  Pillow abra el archivo. El orden es la protección; ver el docstring del módulo.

## Evita

- IMPORTANT: `AuditLog` (modelo concreto en este mismo `models.py`) es **legacy y congelado** —
  ya no recibe filas nuevas desde la unificación de auditoría. No escribas ahí; usa
  `apps.audit.services.log_event` (ver `backend/apps/audit/CLAUDE.md`). El modelo se conserva solo
  por su histórico.
- No agregues `uuid`/soft-delete a `BaseModel` sin revisar el impacto en las tres apps que lo
  heredan — es un cambio transversal, no local a este módulo.
