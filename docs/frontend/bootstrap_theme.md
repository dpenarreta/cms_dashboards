# Integración de la identidad institucional con Bootstrap (Módulo B)

Parte de "Trabajo futuro post-integración con skelleton_base" (ver
`docs/integracion/migration_report.md`, sección "Trabajo futuro completado").

## Qué resuelve

Antes de este módulo, `SiteTheme` (branding) solo alimentaba variables CSS propias del proyecto
(`--color-primary`, `--color-links`, etc., consumidas por `frontend/src/styles/dashboard.css`).
Los componentes de `react-bootstrap` (`<Button variant="primary">`, `<Badge bg="danger">`, los
botones `outline-secondary` del panel de administración, los enlaces `<a>`) seguían pintados con
la paleta por defecto de Bootstrap, sin relación con los colores institucionales configurados en
"Configuración institucional".

## Campos nuevos en `SiteTheme`

`color_success`, `color_danger`, `color_warning`, `color_info`, `color_button_text` —
migración `apps/branding/migrations/0003_agregar_colores_bootstrap.py`, valores por defecto
iguales a la paleta estándar de Bootstrap 5 (`#198754/#dc3545/#ffc107/#0dcaf0/#ffffff`) para no
cambiar el aspecto visual el día que se activa esta configuración.

**Corrección durante la implementación**: la migración de seed `0002_seed_default_theme.py`
importaba `DEFAULT_THEME` en vivo desde `catalog.py` y lo pasaba completo a
`SiteTheme.objects.create(pk=1, **DEFAULT_THEME)`. Al agregarle las 5 claves nuevas al catálogo,
una instalación nueva (que corre todas las migraciones en orden desde cero — exactamente lo que
hace la base de datos de pruebas en cada corrida) fallaba: el modelo histórico congelado en el
estado de la migración 0002 todavía no tenía esos campos. Se corrigió filtrando `DEFAULT_THEME` a
solo los campos que existen en el modelo histórico (`SiteTheme._meta.get_fields()`), para que
agregar campos al catálogo en el futuro no vuelva a romper una instalación desde cero.

## El hallazgo central: Bootstrap precompilado no lee `--bs-primary` en sus componentes

El plan original asumía que bastaba con sobreescribir variables como `--bs-primary` en `:root`
para que `.btn-primary`, `.badge.bg-success`, etc. cambiaran de color. **Se verificó
manualmente en el navegador que esto no es cierto** con el `bootstrap.min.css` precompilado que
ya usa el proyecto: cambiar `color_primary` a un color muy distinto (morado) y sobreescribir solo
`--bs-primary` no modificó el color del botón activo del menú de administración.

Inspeccionando `node_modules/bootstrap/dist/css/bootstrap.min.css`:

```css
.btn-primary{--bs-btn-bg:#0d6efd; --bs-btn-border-color:#0d6efd; ...}
.bg-primary{--bs-bg-opacity:1; background-color:rgba(var(--bs-primary-rgb),var(--bs-bg-opacity))!important}
a{color:rgba(var(--bs-link-color-rgb),var(--bs-link-opacity,1))}
```

- `.btn-primary`/`.btn-outline-primary` fijan sus propias variables internas (`--bs-btn-bg`,
  `--bs-btn-border-color`, `--bs-btn-hover-bg`, ...) con el hexadecimal ya resuelto por Sass en
  tiempo de build — no leen `--bs-primary` en absoluto.
- Las utilidades `.bg-primary`/`.text-primary` sí son dinámicas, pero dependen de
  `--bs-primary-rgb` (una tripleta `"r, g, b"` para usar dentro de `rgba()`), no del propio
  `--bs-primary`.
- Los enlaces (`a`) dependen de `--bs-link-color-rgb`, no de `--bs-link-color`.

Sobreescribir un color de marca en tiempo de ejecución sin recompilar el Sass de Bootstrap
requiere entonces inyectar reglas CSS que redefinan esas variables **directamente sobre la clase
real** (`.btn-primary { --bs-btn-bg: ...; }`), no solo variables sueltas en `:root`.

## Solución implementada

`frontend/src/context/ThemeContext.jsx` genera y mantiene actualizada una hoja de estilos
(`<style id="theme-bootstrap-overrides">`, inyectada en `<head>`) cada vez que se carga o guarda
el tema. Cubre únicamente las clases que la aplicación realmente usa (confirmado por grep de
`variant=`/`bg=` en `frontend/src`): `primary`, `secondary`, `success`, `danger`, `warning`,
`info` — para cada uno genera:

- `.btn-{color}` — fondo/borde/hover/activo/deshabilitado + `color_button_text` como color de
  texto.
- `.btn-outline-{color}` — borde/texto en el color institucional, fondo del color al pasar el
  mouse/activar.
- `.bg-{color}` / `.text-{color}` — con `!important` (igualando la especificidad de las propias
  utilidades de Bootstrap, que también lo usan).
- `a, .btn-link` / `a:hover, .btn-link:hover` — color de enlaces institucional, oscurecido ~20%
  al pasar el mouse (`oscurecer()`, cálculo directo en JS por canal RGB — sin depender de
  `color-mix()` por compatibilidad de navegador).

Verificado visualmente en Chrome: al cambiar `color_primary` a `#7c3aed` y `color_secondary` a
`#eb6834` y guardar, el botón activo del menú de administración, los botones `outline-secondary`
del panel, y los badges de resultado/severidad de la pantalla de auditoría reflejaron los colores
de inmediato.

**Cobertura adicional (tras releer la sección 5.2/5.4 completa del prompt)**: la primera versión
solo cubría botones/badges/enlaces. `.alert-*` (react-bootstrap `<Alert variant="danger">`, usado
en casi todas las páginas de administración y en el login para errores) tiene el mismo problema:
fija sus propias variables `--bs-alert-bg`/`--bs-alert-color`/`--bs-alert-border-color` desde
colores "subtle/emphasis" resueltos por Sass, no desde `--bs-danger`. Se agregó el mismo patrón de
override (`aclarar()`/`oscurecer()` para fondo/borde tenue y texto legible). También se agregó
`.form-check-input:checked`/`:focus` y `.form-control:focus`/`.form-select:focus` (anillo de foco
y casillas/switches marcados), que Bootstrap ata al azul `#0d6efd` por defecto igual que los
botones — cubiertos solo con `color_primary`, como hace el propio Bootstrap (el foco no se
personaliza por color semántico).

## Validación de contraste (WCAG AA)

`frontend/src/utils/colorContrast.js` implementa el cálculo de luminancia relativa y razón de
contraste de WCAG 2.x. `SettingsPage.jsx` compara cada color contra su contraparte real de uso —
no contra negro/blanco absolutos: matemáticamente, **todo color hexadecimal alcanza 4.5:1 contra
al menos uno de los dos extremos** (por la fórmula de contraste de WCAG), así que esa comparación
nunca advertiría nada. En cambio:

- `color_primary`/`color_secondary`/`color_buttons`/`color_success`/`color_danger`/
  `color_warning`/`color_info` se comparan contra `color_button_text` (el texto que realmente
  llevan encima como fondo de botón/badge).
- `color_headings`/`color_text`/`color_links` se comparan contra `color_background`.
- `color_button_text` se compara contra `color_buttons`.

La advertencia (`AvisoContraste`) es puramente informativa — **no bloquea el guardado**, tal
como pide el prompt original.

## Archivos relevantes

- `backend/apps/branding/models.py`, `catalog.py`, `serializers.py`,
  `migrations/0003_agregar_colores_bootstrap.py`, `migrations/0002_seed_default_theme.py` (fix).
- `frontend/src/context/ThemeContext.jsx`, `frontend/src/utils/colorContrast.js`,
  `frontend/src/pages/administration/settings/SettingsPage.jsx`.
- Tests: `backend/apps/branding/tests.py` (sin cambios funcionales, siguen en verde),
  `frontend/src/tests/{ThemeContext,SettingsPage,colorContrast}.test.jsx`.
