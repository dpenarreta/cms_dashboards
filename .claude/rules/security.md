# Seguridad — reglas compartidas

Aplica a `backend/apps/authentication`, `backend/apps/users`, `backend/apps/permissions`,
`backend/apps/audit` y a la carga/exportación de archivos en `backend/cartera`.

## Autenticación y contraseñas

- Las contraseñas se hashean con Argon2 (`PASSWORD_HASHERS`, primero en la lista). Nunca uses
  `usuario.password = ...` directo; usa siempre `usuario.set_password(...)`.
- IMPORTANT: nunca registres contraseñas, tokens JWT, `Authorization`, ni `refresh`/`access` en
  auditoría o logs. `apps.core.audit.mask_sensitive_fields` ya enmascara claves que contengan
  `password`/`token`/`secret`/`refresh`/`access`/`key`/`authorization`/`credential` — reutilízala
  en vez de armar tu propio filtro si agregas un nuevo evento con datos potencialmente sensibles.
- Revocación de sesión es vía el modelo `Session` propio (claim `sid` en el JWT), no vía blacklist
  nativa de `simplejwt` (`BLACKLIST_AFTER_ROTATION = False` a propósito). Para invalidar una
  sesión, marca `revoked_at` en `Session`, no intentes usar `token_blacklist`.
- Protección de fuerza bruta cuenta intentos por **identificador** (username/email), no por
  usuario ya resuelto — evita que enumerar usuarios sea gratis. Si agregas un endpoint de
  autenticación nuevo, replica ese criterio.

## Permisos

- `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` es global (`backend/config/settings.py`). Una
  vista nueva sin `permission_classes` explícito ya exige sesión — no la agregues por las dudas.
- YOU MUST validar permisos en el backend (`require_permission('modulo.accion')`) en toda vista
  nueva que mute datos. Ocultar un botón o un ítem de menú en el frontend nunca es suficiente
  (`frontend/src/config/adminMenu.js` es solo UI).
- `IsSuperuser` (distinto de `require_permission`) es para acciones que ni el catálogo de negocio
  debe poder otorgar (ej. marcar a otro usuario como superusuario). No la uses como atajo genérico
  de "requiere privilegios altos" — solo donde ni un permiso asignable debe bastar.

## Carga y exportación de archivos

- Todo archivo subido se valida por extensión **y** firma binaria (bloquea `.xlsm`/macros
  disfrazadas de `.xlsx`). No aceptes solo la extensión del nombre de archivo. Hay dos
  implementaciones, una por tipo de archivo: `cartera.services.excel_reader.validar_extension_y_firma`
  para el Excel y `apps.core.imagenes` para las imágenes.
- IMPORTANT: en una imagen, la validación de firma tiene que correr **antes** de que Pillow abra el
  archivo, no después. `serializers.ImageField` de DRF llama a `Image.open()` y recién entonces
  valida la extensión, y Pillow elige el parser por la firma del contenido — así que un archivo
  llamado `.png` con contenido PSD llega al parser de PSD igual. Usa `apps.core.imagenes.CampoImagenSegura`
  en cualquier campo de imagen nuevo; no uses `serializers.ImageField` pelado.
- El nombre temporal en disco es siempre un UUID generado en backend, nunca el nombre original
  del archivo del usuario.
- Cualquier valor exportado a CSV/Excel que empiece con `= + - @` se sanitiza antes de escribirlo
  (anti inyección de fórmulas). Reutiliza `cartera.services.export_service`, no escribas un
  exportador nuevo sin ese saneo.

## Auditoría

- `apps.audit.services.log_event` nunca lanza excepción — una falla al auditar no debe interrumpir
  la operación de negocio. Si escribes un evento nuevo, no lo envuelvas en `try/except` adicional,
  ya está cubierto.
- No escribas directo en `apps.core.AuditLog` ni en `cartera.DashboardAuditLog` desde código
  nuevo — son tablas legacy congeladas. Todo evento nuevo pasa por `log_event(domain=..., ...)`.
