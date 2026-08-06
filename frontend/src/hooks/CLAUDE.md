# hooks/

Hereda `../../CLAUDE.md`. Un hook por flujo de negocio reutilizable — si la lógica solo la usa una
página, considera si de verdad necesita ser un hook aparte.

## Inventario (10 hooks)

- `useAdminMenu.js` — filtra el menú admin estático según `user.permissions`.
- `useCarteraDashboard.js` — orquesta carga/mapeo/dashboard del flujo legado de cartera.
- `useColorMode.js` — toggle claro/oscuro, persistido en `localStorage`, coordinado con
  `ThemeContext` (ver `../context/CLAUDE.md`).
- `useDashboardLayout.js` — CRUD del layout de un dashboard real: cargar, guardar (maneja el 409
  de versión), reset, mover/reordenar.
- `useDetalleCartera.js` — paginación/orden/búsqueda del detalle de cartera contra backend.
- `useDrilldown.jsx` — `DrilldownProvider`/context para el panel de detalle y sus filtros
  acumulados.
- `useGenericDashboardBuilder.js` — flujo CARGA → RENOMBRAR → VALORES_EN_BLANCO (condicional) →
  MAPEO para la plantilla fija de 15 posiciones.
- `usePaginacionCliente.js` — paginación 100% en memoria, sin volver a pedir al backend.
- `usePermisos.js` — ver advertencia abajo.
- `usePlantillaBaseLayout.js` — igual a `useDashboardLayout.js` pero para la plantilla base del
  sistema.

## IMPORTANT: `usePermisos.js` es un stub

Este hook concede **todos** los permisos del editor visual siempre, sin verificar nada — es un
placeholder previo a la integración de permisos reales. No lo confundas con `user.permissions`
(`AuthContext`), que sí refleja permisos reales resueltos por el backend. Si vas a condicionar una
acción del editor visual por permiso real, usa `user.permissions.includes('dashboard.xxx')`
directamente, no `usePermisos()`. La protección real de todas formas ocurre en el backend
(`require_permission`) — este hook nunca fue, ni debe tratarse como, la barrera de seguridad.

## Evita

- No dupliques la lógica de manejo de error (`.catch(e => setError(e.response?.data?.mensaje))`)
  con un patrón distinto al que ya usan estos hooks — es intencionalmente repetitivo pero
  consistente en todo el proyecto.
