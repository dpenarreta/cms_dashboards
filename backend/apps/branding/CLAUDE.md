# Módulo: branding

Hereda `../../CLAUDE.md`.

## Responsabilidad

Identidad institucional consolidada: nombre, logo/favicon, 13 colores, tipografía, radio de
bordes. Fuente única de verdad para landing pública, login y app autenticada.

## Estructura

- `models.py` — `SiteTheme(BaseModel)`: **singleton forzado a `pk=1`** (`save()` fija
  `self.pk = 1`). `delete()` lanza `NotImplementedError` a propósito — la configuración se
  restablece, no se elimina.
- `catalog.py` — `DEFAULT_THEME` (valores por defecto, replican la paleta que ya usaba
  `dashboard.css` antes de este módulo, para no cambiar el aspecto visual al activarlo).
- `validators.py` — regex hex `#RGB`/`#RRGGBB`, fuentes/border-radius contra listas cerradas de
  `catalog.py`, tamaño de fuente `\d{1,2}px`.

## Reglas

- IMPORTANT: nunca instancies `SiteTheme(...)` directo — siempre `SiteTheme.get_solo()`
  (`get_or_create(pk=1, ...)`). Instanciar directo pisaría la fila existente sin conservar su
  `created_at` original.
- `GET /api/branding/current` es el único endpoint público (`AllowAny`) de todo el backend además
  de login/refresh — lo consumen landing y login sin sesión. No le agregues datos que no deban ser
  públicos (ej. nunca expongas ahí nada de usuarios).
- Bootstrap precompilado (`bootstrap.min.css`) no lee `--bs-primary` en tiempo de ejecución en sus
  componentes reales (`.btn-primary` fija su propio `--bs-btn-bg` resuelto en build) — cambiar un
  color acá no repinta botones/badges/alerts por sí solo. La solución (hoja `<style>` inyectada
  con overrides por clase real) vive en `frontend/src/context/ThemeContext.jsx`, no en este
  módulo — si agregas un color nuevo acá, coordina el override correspondiente ahí. Detalle en
  `docs/frontend/bootstrap_theme.md`.

## Evita

- No agregues un segundo modelo de configuración institucional "más simple" — `SiteTheme` ya es el
  único, y duplicar el patrón singleton en otro modelo es la misma trampa que ya se evitó una vez.
