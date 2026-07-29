# Dashboard de Cartera — gráficos interactivos y drill-down

Este documento complementa el `README.md` con el detalle de la interactividad agregada sobre
el dashboard: qué gráficos abren detalle, qué filtro generan y cómo se conserva el contexto.

## Patrón de navegación

El proyecto no tenía (ni tiene) un router de páginas — es una sola vista con fases locales
(`CARGA` → `MAPEO` → `DASHBOARD`). En vez de agregar `react-router` solo para el drill-down, el
detalle se implementó como un **panel lateral reutilizable** (`Offcanvas` de react-bootstrap:
`PortfolioDetailPanel`). Al ser una superposición sobre el dashboard, "volver" es simplemente
cerrar el panel: los filtros globales, la fecha de corte y el scroll de la página de fondo
nunca se tocan, así que el contexto se conserva automáticamente.

## Contrato de filtros (drill-down)

Toda selección visual pasa por un único hook de contexto, `useDrilldown`
(`frontend/src/hooks/useDrilldown.jsx`):

```js
const { abrirDetalle } = useDrilldown()

abrirDetalle({
  origen: 'cartera_vencida_por_ciudad',
  titulo: 'Cartera vencida de Quito',
  filtros: { estado_cartera: 'VENCIDA', ciudad: 'QUITO' },
})
```

`abrirDetalle` solo guarda `{origen, titulo, filtros}` en el contexto; `PortfolioDetailPanel`
combina esos `filtros` (los "de drill-down") con los filtros globales del dashboard
(`filtrosGlobales`, que le llegan como prop normal desde `CarteraDashboardPage`) y los pasa a
`DetalleTable`, que a su vez usa el hook compartido `useDetalleCartera` para paginar/ordenar/
buscar — el mismo hook que usa la tabla de detalle principal del dashboard, para no duplicar esa
lógica en cada lugar donde se muestra un detalle.

## Gráficos e indicadores interactivos, y el filtro que generan

| Componente | Selección | Filtro generado |
|---|---|---|
| `CarteraVencidaPorCiudadChart` (pastel) | Segmento o fila de leyenda de una ciudad | `estado_cartera=VENCIDA`, `ciudad=<ciudad>` |
| `CarteraVencidaPorCiudadChart` | Segmento "Otras ciudades" | `estado_cartera=VENCIDA`, `ciudad=<c1,c2,...>` (lista separada por comas) |
| `TopClientesChart` | Barra de un cliente | `cliente=<ruc>` |
| `RecuperadoresChart` | Barra de un recuperador | `recuperador=<recuperador>` (sin restringir estado de cartera) |
| `CausalesChart` (dona/barras) | Segmento/barra/leyenda de una causal | `causal=<causal>` |
| `CausalesChart` | Categoría "OTRAS" | `causal=<c1,c2,...>` |
| `RecuperadorCausalChart` (barras apiladas) | Segmento de causal dentro de la barra de un recuperador | `recuperador=<recuperador>`, `causal=<causal>` |
| `RecuperadorCausalMatrix` | Celda | `recuperador=<fila>`, `causal=<columna>` |
| `RecuperadorCausalMatrix` | Total de fila / total de columna | Solo `recuperador=<fila>` / solo `causal=<columna>` |
| `KpiCard` — Cartera vencida | Tarjeta completa | `estado_cartera=VENCIDA` |
| `KpiCard` — Cartera no vencida | Tarjeta completa | `estado_cartera=NO VENCIDA` |
| `KpiCard` — Cartera > 120 días | Tarjeta completa | `estado_cartera=VENCIDA`, `dias_vencidos_min=121` |
| `KpiCard` — Cartera > 360 días | Tarjeta completa | `estado_cartera=VENCIDA`, `dias_vencidos_min=361` |
| `KpiCard` — Clientes únicos / Cartera total | Tarjeta completa | Ninguno adicional (abre el detalle con solo los filtros globales activos) |

`dias_vencidos_min`/`dias_vencidos_max` y los valores separados por comas en `ciudad`/`causal`/
`recuperador`/etc. son extensiones nuevas del contrato de filtros del backend — ver
`docs/api-reference.md`.

## Nota de diseño: el título del panel no cambia al quitar un filtro

El título del panel (p. ej. "Cartera vencida de QUITO") describe la selección que **abrió** el
panel — es un rótulo de origen, no un resumen recalculado. Si el usuario quita después el chip
"Ciudad: QUITO", la tabla se actualiza correctamente (vuelve a mostrar todas las ciudades), pero
el título no se reescribe. La fuente de verdad sobre qué se está filtrando en ese momento son
los chips de `ActiveFiltersSummary`, no el título. Se documenta explícitamente para que no se
confunda con un defecto: recalcular un título genérico a partir de una combinación arbitraria de
filtros removidos uno por uno añadiría complejidad sin mejorar la precisión de la información
(los chips ya la dan).

## Conservación de filtros globales

`ActiveFiltersSummary` distingue visualmente los filtros **globales** (los que ya estaban
activos en el panel de filtros del dashboard — chip gris, no removible desde el panel) de los
filtros **de drill-down** (los que generó la selección del gráfico — chip azul, con botón para
quitarlo). Quitar un filtro de drill-down no afecta los filtros globales ni reprocesa el
archivo; solo vuelve a consultar el detalle con el filtro combinado restante.

## Permisos y auditoría

El proyecto **no implementa autenticación** (decisión documentada desde la entrega inicial). Por
lo tanto:

- No existe validación de permisos por usuario en el backend para el drill-down — cualquier
  cliente que pueda llamar a la API puede consultar cualquier `carga_id` que conozca (mismo
  nivel de exposición que el resto de la aplicación).
- No hay registro de auditoría de quién abrió qué detalle.

Si se necesita esto, requiere agregar un sistema de autenticación como trabajo aparte; los
criterios de aceptación relacionados (`AC-CAR-009`) están marcados como "No aplica" en
`tests/qa/acceptance-criteria-traceability.md`, no como aprobados.

## Paginación y rendimiento

El panel de detalle y la tabla principal comparten `useDetalleCartera`, que siempre consulta al
backend con `page`/`page_size` (por defecto 50) — nunca se descarga la cartera completa al
navegador para filtrarla en el cliente.

## Limitación conocida — teclado en marcas SVG

Los sectores de pastel, barras y segmentos apilados de Recharts no son elementos DOM enfocables
de forma nativa. El foco de teclado está implementado en las afordancias HTML que acompañan a
cada gráfico (leyendas-lista con `<button>`, tarjetas KPI y celdas de la matriz), pero
`RecuperadoresChart`, `TopClientesChart` y `RecuperadorCausalChart` todavía no tienen una
leyenda-lista equivalente para accionar su drill-down solo con teclado. Ver la matriz de
trazabilidad para el detalle exacto de qué quedó cubierto por prueba automatizada.
