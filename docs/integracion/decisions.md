# Decisiones de arquitectura — integración skelleton_base

## Decisión 1: Estructura de apps backend

**Contexto**: skelleton_base organiza su backend en `apps/<nombre>` (core, permissions,
authentication, users, roles, branding). cms_dashboards tiene una única app `cartera` en la raíz
de `backend/`.

**Opciones analizadas**:
- Mover `cartera` dentro de `backend/apps/cartera/` para uniformar.
- Dejar `cartera` donde está y crear `backend/apps/` como paquete nuevo, aparte.

**Alternativa seleccionada**: dejar `cartera` en su ubicación actual; crear `backend/apps/` solo
para las apps nuevas.

**Motivo**: mover `cartera` tocaría el `app_label` (usado en migraciones y en `ContentType`),
todos los imports internos, `INSTALLED_APPS`, y arriesgaría las 77 pruebas existentes, sin ningún
beneficio funcional — es reorganización por estética, no por necesidad, y el propio prompt de
integración pide explícitamente "no reorganices todo el proyecto sin necesidad".

**Impacto**: `INSTALLED_APPS` queda con `cartera` y `apps.core`/`apps.permissions`/etc. como
entradas hermanas, no anidadas.

**Archivos afectados**: `backend/config/settings.py`.

---

## Decisión 2: Modelo de usuario

**Contexto**: cms_dashboards nunca definió un modelo de usuario propio (no hay autenticación).
skelleton_base requiere `AUTH_USER_MODEL = "users.User"` (`AbstractUser` extendido).

**Opciones analizadas**:
- Usar el modelo `User` por defecto de Django + un modelo `Perfil` aparte relacionado 1:1.
- Adoptar directamente el `User(AbstractUser, BaseModel)` de skelleton_base.

**Alternativa seleccionada**: adoptar directamente el modelo de skelleton_base.

**Motivo**: el usuario confirmó que no hay datos de producción ni migraciones desplegadas que
dependan del modelo de usuario por defecto de Django. Cambiar `AUTH_USER_MODEL` es solo seguro
antes de la primera migración real — este es exactamente ese momento. Evita mantener dos modelos
(`User` + `Perfil`) para un beneficio nulo.

**Impacto**: `AUTH_USER_MODEL = "users.User"`. Sin campo "área" (no lo pide ningún criterio de
aceptación explícito de la sección 11 del prompt; se puede agregar después sin romper nada).

**Archivos afectados**: `backend/apps/users/models.py`, `backend/config/settings.py`.

---

## Decisión 3: Roles como `Group` nativo

**Contexto**: "rol" necesita ser administrable (crear/editar/eliminar, asignar permisos).

**Opciones analizadas**:
- Modelo `Role` propio con tabla `role_permissions` M2M propia.
- Reutilizar `django.contrib.auth.models.Group` (ya trae M2M con `Permission`).

**Alternativa seleccionada**: `Group`.

**Motivo**: es exactamente el mismo enfoque ya validado en skelleton_base, reutiliza
infraestructura nativa de Django (admin, migraciones, `user.groups`), y significa menos código
propio que mantener y auditar por seguridad.

**Impacto**: "Rol" en la UI administrativa es 1:1 con `Group` en la base de datos.

**Archivos afectados**: `backend/apps/roles/views.py`, `serializers.py`.

---

## Decisión 4: Catálogo de permisos unificado

**Contexto**: cms_dashboards ya tiene 7 permisos (`dashboard.view`, `dashboard.edit`,
`dashboard.layout.edit`, `dashboard.component.style`, `dashboard.component.create`,
`dashboard.component.delete`, `dashboard.configuration.reset`) verificados hoy por un stub que
siempre concede todo (`cartera/permisos.py`). skelleton_base trae 13 permisos propios
(usuarios/roles/permisos/configuración/auditoría) anclados a un `ModulePermission` con
`managed=False`.

**Opciones analizadas**:
- Dos catálogos de permisos separados (uno para `cartera`, otro para `apps.*`).
- Un único catálogo (`apps/permissions/catalog.py`) que incluye los 7 de `cartera` + los 13 de
  skelleton_base.

**Alternativa seleccionada**: un único catálogo.

**Motivo**: el prompt exige "una única fuente de verdad" para permisos. Mantener el nombre exacto
de los 7 permisos de `dashboard.*` evita tocar los ~20 call-sites de `tiene_permiso(request,
DASHBOARD_XXX)` ya existentes en `cartera`.

**Impacto**: `PERMISSION_CATALOG` en `apps/permissions/catalog.py` tiene 20 entradas. La migración
de datos de `apps.permissions` crea los 20 `Permission` reales bajo el `ContentType` de
`ModulePermission`.

**Archivos afectados**: `backend/apps/permissions/catalog.py`, `backend/apps/permissions/migrations/0001_initial.py`.

---

## Decisión 5: Nombre del rol administrador

**Contexto**: skelleton_base siembra un grupo llamado "Superusuario" con el catálogo completo de
permisos. El prompt de integración pide explícitamente un rol llamado `ADMINISTRADOR_GENERAL`.

**Alternativa seleccionada**: renombrar el grupo sembrado a `ADMINISTRADOR_GENERAL`.

**Motivo**: instrucción explícita y repetida del usuario (sección 15 del prompt). Se mantiene el
mismo criterio de diseño que ya traía skelleton_base: el acceso "administrador" no depende del
nombre del grupo, sino de que el backend siga validando permisos individualmente — el grupo es
solo un atajo para asignar el catálogo completo a una cuenta.

**Impacto**: migración de datos `apps/roles/migrations/0002_seed_administrador_general.py`.

**Archivos afectados**: `backend/apps/roles/migrations/0002_seed_administrador_general.py`.

---

## Decisión 6: `cartera/permisos.py` cambia de comportamiento, no de contrato

**Contexto**: hoy `permisos_del_usuario(request)` devuelve `True` para todos los permisos siempre.
El prompt exige activar autenticación/autorización real, pero también exige explícitamente "no
sacrificar funcionalidades actuales" y que "ningún dashboard existente deje de funcionar".

**Opciones analizadas**:
- Activar `IsAuthenticated` global + resolver permisos reales en la misma fase que se crean los
  modelos de usuario/roles/permisos.
- Crear los modelos y la resolución de permisos reales ahora, pero mantener el fallback "todo
  permitido" cuando no hay usuario autenticado, hasta que el frontend tenga login (fase futura).

**Alternativa seleccionada**: la segunda — fallback abierto hasta la fase de protección.

**Motivo**: el frontend todavía no tiene página de login ni interceptor JWT (eso es la Fase 4,
explícitamente posterior). Si se exige autenticación ahora, el dashboard de Cartera quedaría
inaccesible en el navegador hasta completar el frontend — una regresión funcional real, que el
criterio de aceptación del prompt prohíbe expresamente ("no consideres terminada la tarea
mientras algún dashboard existente deje de funcionar").

**Impacto**: `permisos_del_usuario` ya sabe resolver permisos reales desde
`request.user.get_all_permissions()` cuando hay sesión, pero sigue devolviendo `True` para todos
cuando `request.user` no está autenticado. Este fallback se retira explícitamente en la Fase 5.

**Archivos afectados**: `backend/cartera/permisos.py`.

---

## Decisión 7: Contrato de error único

**Contexto**: cartera usa `{"error": <codigo>, "mensaje": <texto>, "detalles": {...}}` (via
`cartera_exception_handler`, que delega primero a `rest_framework.views.exception_handler` para
errores estándar de DRF). skelleton_base usa `{"error": {"code": ..., "message": ..., "details":
...}}` (anidado).

**Alternativa seleccionada**: todo el backend (incluidas las apps nuevas) usa el contrato ya
existente de `cartera` — las nuevas vistas lanzan `cartera.exceptions.CarteraError` para errores
de negocio (credenciales inválidas, cuenta bloqueada, etc.).

**Motivo**: el prompt exige evitar funcionalidades/sistemas duplicados; tener dos contratos de
error activos simultáneamente en la misma API sería exactamente ese tipo de duplicidad, y
obligaría al frontend a manejar dos formatos distintos según el endpoint.

**Impacto**: `EXCEPTION_HANDLER` en `REST_FRAMEWORK` sigue siendo
`cartera.exceptions.cartera_exception_handler`, sin cambios. Las respuestas 401/403 de DRF
(`NotAuthenticated`/`PermissionDenied`, cuando se activen en fases futuras) usan el shape
`{"detail": "..."}` estándar de DRF (ya soportado por ese handler), y los errores de negocio de
`apps.authentication`/`apps.users`/`apps.roles` usan `{"error","mensaje","detalles"}`.

**Archivos afectados**: `backend/apps/authentication/services.py`, `backend/apps/users/services.py`,
`backend/apps/roles/views.py`.

---

## Decisión 8: JWT sin blacklist nativa, con revocación vía `Session` propio

**Contexto**: `djangorestframework-simplejwt` ofrece un mecanismo nativo de blacklist
(`token_blacklist`), pero requiere su propia tabla y app.

**Alternativa seleccionada**: no activar `token_blacklist`; usar el modelo `Session` propio (claim
`sid` en el JWT) para poder revocar/expirar sesiones sin depender del mecanismo genérico.

**Motivo**: igual decisión ya validada en skelleton_base — permite invalidar sesiones específicas
(ej. al deshabilitar un usuario), listar sesiones activas por usuario, y evita una tabla adicional
redundante con el mismo propósito.

**Impacto**: `SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] = False`, `rest_framework_simplejwt.token_blacklist`
no se agrega a `INSTALLED_APPS`.

**Archivos afectados**: `backend/config/settings.py`, `backend/apps/authentication/models.py`.

---

## Decisión 9: Auditoría — coexistencia temporal, no unificación inmediata

**Contexto**: `cartera.DashboardAuditLog` (cambios de layout del editor visual: orden, tamaño,
color, texto, configuración, ocultado, restablecido) ya existe y tiene 77 pruebas dependiendo de
su esquema exacto. El nuevo `apps.core.AuditLog` (genérico: actor/acción/módulo/entidad/ip/ua) es
para eventos de seguridad (login, cambios de usuario/rol/permiso).

**Opciones analizadas**:
- Unificar ambos en un solo modelo genérico ahora.
- Mantenerlos separados por dominio (seguridad vs. configuración visual), documentando la
  posibilidad de unificar después.

**Alternativa seleccionada**: mantenerlos separados en esta fase.

**Motivo**: unificarlos implica migrar `DashboardAuditLog` (con sus campos específicos
`dashboard_id`/`component_id`/`version`/`previous_config`/`new_config`) al esquema genérico de
`AuditLog`, reescribiendo `dashboard_layout.py` (`aplicar_layout`, `restablecer_layout`, y el
endpoint `/versions`) y sus pruebas — un cambio de alto riesgo para una app con historial real de
uso, sin beneficio funcional inmediato. Se prioriza no romper lo existente sobre la pureza
arquitectónica.

**Impacto**: por ahora coexisten dos tablas de auditoría con propósitos distintos y
explícitamente documentados. Esto **no** se considera "duplicidad" en el sentido que prohíbe el
prompt (que se refiere a sistemas competidores del mismo dominio, como dos sistemas de auth o dos
modelos de usuario) — son dominios de negocio distintos. Se deja como ítem de seguimiento
explícito en `migration_report.md` para una fase futura de unificación si se decide que aporta
valor.

**Archivos afectados**: ninguno en esta fase (decisión de diseño, no de código).

---

## Decisión 10: Recuperación de contraseña por email diferida

**Contexto**: skelleton_base incluye un flujo completo de "olvidé mi contraseña" vía email
(`PasswordResetToken` + `emails.py`).

**Alternativa seleccionada**: diferir este flujo a una fase futura.

**Motivo**: la sección 10 del prompt (integración del sistema de autenticación) lista
explícitamente qué se debe incorporar — login, logout, refresh, JWT, hash, usuario
activo/expiración, protección de rutas, interceptores, token expirado, redirección, manejo de
errores — y no menciona recuperación de contraseña por email. Incluirlo ahora requeriría
configurar SMTP (`EMAIL_HOST`, credenciales) sin que el usuario lo haya pedido ni provisto,
inflando el alcance de esta fase sin necesidad.

**Impacto**: `ChangeOwnPasswordView` (cambio de contraseña estando autenticado) sí se implementa
(cubre "must_change_password"); el flujo de "olvidé mi contraseña" sin sesión queda pendiente.

**Archivos afectados**: `backend/apps/authentication/views.py` (no incluye
`PasswordResetRequestView`/`PasswordResetConfirmView` en esta fase).

---

## Decisión 11: Un único `requirements.txt`

**Contexto**: skelleton_base separa `requirements/base|dev|prod.txt`; cms_dashboards usa un único
`requirements.txt`.

**Alternativa seleccionada**: mantener un único `requirements.txt`, agregando
`djangorestframework-simplejwt` y `argon2-cffi` ahí.

**Motivo**: el prompt indica explícitamente "utiliza únicamente el gestor de paquetes definido en
cms_dashboards, salvo justificación documentada" — no hay justificación de peso para introducir el
split (el proyecto es pequeño, no tiene pipeline de CI que se beneficie de separar dev/prod hoy).

**Impacto**: `backend/requirements.txt` crece con 2 líneas nuevas.

**Archivos afectados**: `backend/requirements.txt`.

---

## Decisión 12: Django `TestCase` en vez de pytest

**Contexto**: skelleton_base usa `pytest` + `pytest-django` + `pytest-bdd`; cms_dashboards usa
Django `TestCase`/`APITestCase` puro (77 pruebas ya existentes).

**Alternativa seleccionada**: Django `TestCase`/`APITestCase` para todo el backend (decisión
explícita confirmada con el usuario).

**Motivo**: introducir un segundo framework de pruebas en el mismo backend es exactamente el tipo
de "duplicidad de tooling" que el prompt pide evitar, y obligaría a mantener dos comandos de
ejecución (`manage.py test` y `pytest`) y dos configuraciones en el README y en CI.

**Impacto**: toda la lógica de pruebas portada desde skelleton_base se reescribe en estilo
`TestCase`/`APITestCase`, sin usar `pytest-django`/`factory-boy`/`pytest-bdd`.

**Archivos afectados**: `backend/apps/*/tests.py`.

---

## Decisión 13: `react-router-dom@7.18.2` (última versión) pese a la advertencia de `npm audit`

**Contexto**: skelleton_base usa `react-router-dom@6.28` (React 18). cms_dashboards adopta React
19 + Vite 8, así que se evaluó qué versión de `react-router-dom` instalar. `npm audit` marca
`react-router-dom@7.18.2` (última) con una vulnerabilidad "alta": *RSC Mode CSRF Bypass Allows
Action Execution Before 400 Response*, y solo ofrece como "fix" bajar a `7.11.0`.

**Alternativa seleccionada**: mantener `7.18.2` (la última), no degradar a `7.11.0`.

**Motivo**: la vulnerabilidad marcada afecta exclusivamente el "RSC Mode" (React Server
Components/acciones de servidor de React Router) — una funcionalidad que este proyecto no usa en
absoluto (se usa únicamente enrutamiento declarativo del lado del cliente: `BrowserRouter`,
`Routes`, `Route`, contra un backend Django REST completamente separado, sin acciones ni loaders
de servidor de React Router). Al probar `7.11.0` con `npm audit`, esa versión anterior expone
otras vulnerabilidades que sí aplican a nuestro uso real (open redirect vía `<Link>`/`useNavigate`,
XSS, DoS por resolución de rutas ineficiente) — vulnerabilidades que las versiones posteriores
(incluida 7.18.2) ya corrigieron. Degradar habría cambiado un riesgo inaplicable por riesgos reales.

**Impacto**: `frontend/package.json` fija `react-router-dom@^7.18.2`. Revisar este `npm audit` en
el futuro si la librería publica un parche para el modo RSC, aunque no cambia el análisis de
riesgo mientras el proyecto no use esa funcionalidad.

**Archivos afectados**: `frontend/package.json`.
