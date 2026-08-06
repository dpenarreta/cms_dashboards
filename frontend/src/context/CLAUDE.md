# context/

Hereda `../../CLAUDE.md`. Solo dos contexts en todo el proyecto — no hay estado global tipo
Redux/Zustand, y no se debe introducir uno sin justificarlo.

## `AuthContext.jsx`

Sesión global: `user`, `isAuthenticated`, `isInitializing`, `login`, `logout`, `refreshUser`.
`user.permissions` ya trae el catálogo completo resuelto para superusuarios — es la fuente de
verdad para gatear UI, no `user.is_superuser` directo.

## `ThemeContext.jsx`

Carga la identidad institucional pública (`GET /branding/current`, sin sesión) y la aplica al DOM:
variables CSS + una hoja `<style>` inyectada dinámicamente.

- IMPORTANT: Bootstrap 5.3 precompilado **no** lee `--bs-primary` en sus componentes reales
  (`.btn-primary` fija su propio `--bs-btn-bg` ya resuelto en build por Sass). Cambiar un color de
  marca requiere sobreescribir la variable interna de cada clase real (`.btn-primary { --bs-btn-bg:
  ...}`), no solo una variable suelta en `:root` — por eso este archivo inyecta una hoja `<style>`
  completa en vez de solo `setProperty` en `:root`. Si agregas un componente Bootstrap nuevo que
  deba respetar el color institucional (ej. un `variant` no cubierto), agrega su override acá
  siguiendo el mismo patrón — no asumas que ya funciona solo. Detalle en
  `docs/frontend/bootstrap_theme.md`.
- Coordina con `useColorMode.js` (modo oscuro): ambos escriben `--color-background` en el mismo
  elemento (`documentElement`), y `useColorMode` depende de `theme` en su `useEffect` para
  reaplicar el oscuro cada vez que `ThemeContext` (re)carga — si tocas uno, revisa el otro.

## Evita

- No leas `document.documentElement.style` directo desde un componente para decidir el tema
  actual — usa `useTheme()`/`useColorMode()`.
