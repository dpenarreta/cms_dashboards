# components/

Hereda `../../CLAUDE.md`. Componentes agrupados por dominio, no por tipo (no hay carpeta genérica
"UI" además de `common/`).

## Responsabilidad por subcarpeta

- `admin/` — `AdminLayout`/`AdminSidebar`: layout de pantalla completa con sidebar, compartido por
  dashboards y administración.
- `auth/` — `RequirePermission`: guard de rutas por permiso.
- `charts/` — gráficos específicos del dashboard "legado" de cartera (cartera vencida por ciudad,
  causales, recuperador×causal, top clientes).
- `common/` — genéricos reutilizables sin dominio propio (ej. `Pagination.jsx`).
- `dashboard-editor/` — editor visual de layout: grid editable, paleta de componentes, panel de
  propiedades, toolbar de modo edición, modales. Ver `@.claude/rules/dashboards.md` antes de
  tocar cualquier cosa acá — dos `DndContext` independientes a propósito, no los fusiones.
- `dashboard-generic/` — renderers data-driven reutilizables (barras, líneas, pastel, dispersión,
  área apilada, tabla, KPI, separador, título, tabla histórica) + pasos del wizard de carga
  genérico. Un renderer nuevo debe usar `var(--series-N)` para colores de serie, no hex fijos
  (para que el modo oscuro lo re-temee gratis).
- `dashboards/` — `DashboardTabsBar`: pestañas de un dashboard.
- `drilldown/` — resumen de filtros activos y panel de detalle (`Offcanvas`, no una ruta nueva).
- `filters/` — panel de filtros del dashboard legado.
- `kpi/` — tarjetas/fila de KPIs del dashboard legado.
- `mapping/` — tabla de mapeo columna-origen → posición de plantilla.
- `public/` — navbar de páginas públicas (landing/login), fuera del `AdminLayout`.
- `table/` — tabla de detalle paginado de cartera.
- `upload/` — zona de carga de archivo (drag & drop).

## Reglas

- Un componente de `dashboard-generic/` no debe importar nada de `dashboard-editor/` — el sentido
  de la dependencia es editor → genérico (el editor decide qué renderer mostrar), nunca al revés.
- Componentes que necesiten drag & drop fuera de `dashboard-editor/`: revisa primero si
  `@dnd-kit/core`/`sortable` ya resuelve el caso antes de introducir otra librería de DnD.
