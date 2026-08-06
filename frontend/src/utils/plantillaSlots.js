/**
 * Espejo de `cartera/services/plantilla.py::PLANTILLA_SLOTS` — las 15 posiciones fijas de la
 * plantilla de dashboard, usado por `TemplateMappingStep` para saber qué campos de columna
 * mostrar por posición (`calculo`) y cómo previsualizarla (`tipoVisualizacion`/`configFijo`).
 */

// Espejo de `cartera/services/plantilla.py::DASHBOARD_ID_PLANTILLA_BASE` — el `dashboard_id`
// reservado de la plantilla base, usado por `PlantillaBasePage` para pedir su propia tabla
// histórica (Tabla 4/Tabla 5) igual que cualquier dashboard real.
export const DASHBOARD_ID_PLANTILLA_BASE = 'plantilla-base-sistema'
export const PLANTILLA_SLOTS = [
  { id: 'kpi-1', titulo: 'KPI 1', grupo: 'KPI', tipoVisualizacion: 'kpi', calculo: 'kpi', colorDefecto: '#2a78d6', configFijo: { icono: 'persona' } },
  { id: 'kpi-2', titulo: 'KPI 2', grupo: 'KPI', tipoVisualizacion: 'kpi', calculo: 'kpi', colorDefecto: '#1baf7a', configFijo: { icono: 'dolar' } },
  { id: 'kpi-3', titulo: 'KPI 3', grupo: 'KPI', tipoVisualizacion: 'kpi', calculo: 'kpi', colorDefecto: '#8b5cf6', configFijo: { icono: 'carrito' } },
  { id: 'kpi-4', titulo: 'KPI 4', grupo: 'KPI', tipoVisualizacion: 'kpi', calculo: 'kpi', colorDefecto: '#eda100', configFijo: { icono: 'grafico' } },
  { id: 'grafico-1', titulo: 'Gráfico 1', grupo: 'Gráficos', tipoVisualizacion: 'barras_verticales', calculo: 'chart', configFijo: {} },
  { id: 'grafico-2', titulo: 'Gráfico 2', grupo: 'Gráficos', tipoVisualizacion: 'lineas_multiples', calculo: 'multivalor', configFijo: {} },
  { id: 'grafico-3', titulo: 'Gráfico 3', grupo: 'Gráficos', tipoVisualizacion: 'area_apilada', calculo: 'multiserie', configFijo: {} },
  { id: 'grafico-4', titulo: 'Gráfico 4', grupo: 'Gráficos', tipoVisualizacion: 'dona', calculo: 'chart', configFijo: { mostrar_total: true } },
  { id: 'grafico-5', titulo: 'Gráfico 5', grupo: 'Gráficos', tipoVisualizacion: 'pastel', calculo: 'chart', configFijo: {} },
  { id: 'grafico-6', titulo: 'Gráfico 6', grupo: 'Gráficos', tipoVisualizacion: 'dispersion', calculo: 'dispersion', configFijo: {} },
  { id: 'tabla-1', titulo: 'Tabla 1', grupo: 'Tablas', tipoVisualizacion: 'tabla', calculo: 'tabla', configFijo: {} },
  { id: 'tabla-2', titulo: 'Tabla 2', grupo: 'Tablas', tipoVisualizacion: 'tabla', calculo: 'tabla', configFijo: {} },
  { id: 'tabla-3', titulo: 'Tabla 3', grupo: 'Tablas', tipoVisualizacion: 'tabla', calculo: 'tabla', configFijo: {} },
  { id: 'tabla-4', titulo: 'Tabla 4', grupo: 'Tablas', tipoVisualizacion: 'tabla', calculo: 'tabla', configFijo: {} },
  { id: 'tabla-5', titulo: 'Tabla 5', grupo: 'Tablas', tipoVisualizacion: 'tabla', calculo: 'tabla', configFijo: {} },
]

export const ETIQUETAS_TIPO_VISUALIZACION = {
  kpi: 'Tarjeta KPI',
  barras_verticales: 'Barras verticales',
  barras_horizontales: 'Barras horizontales',
  lineas: 'Líneas',
  lineas_multiples: 'Líneas múltiples',
  barras_agrupadas: 'Barras agrupadas',
  barras_apiladas: 'Barras apiladas',
  area_apilada: 'Área apilada',
  dona: 'Dona',
  pastel: 'Pastel',
  dispersion: 'Dispersión',
  tabla: 'Tabla',
}

/**
 * Tipos de visualización entre los que se puede cambiar una posición sin cambiar su `calculo`
 * (mismos datos calculados) — espejo de `cartera/services/plantilla.py::TIPOS_COMPATIBLES`. KPI,
 * dispersión y tabla no aparecen: su `calculo` solo se puede dibujar de una forma.
 *
 * `pastel`/`dona` también aparecen en `multivalor`/`multiserie` (2+ columnas de valor) aunque un
 * gráfico circular solo puede mostrar una porción por categoría: `GenericChartRenderer` colapsa
 * automáticamente las columnas/series en una sola (sumadas por categoría) cuando se elige uno de
 * estos dos tipos sobre una posición de varias columnas — el usuario no tiene que rehacer el
 * mapeo para "bajar" a una sola columna.
 */
export const TIPOS_COMPATIBLES = {
  chart: ['barras_verticales', 'barras_horizontales', 'lineas', 'pastel', 'dona'],
  multivalor: ['barras_agrupadas', 'barras_apiladas', 'area_apilada', 'lineas_multiples', 'pastel', 'dona'],
  multiserie: ['barras_agrupadas', 'barras_apiladas', 'area_apilada', 'lineas_multiples', 'pastel', 'dona'],
}

/**
 * Agrupación semántica de las 13 posiciones fijas en las 5 "zonas" del patrón Z (sección 9,
 * `PLANTILLA_SLOTS` en `cartera/services/plantilla.py`), usada por `EditableGrid` en modo edición
 * para delimitar visualmente cada zona con un recuadro punteado y su rótulo — así se ve de un
 * vistazo dónde va cada bloque, incluso antes de mirar el contenido de cada posición.
 */
export const ZONAS_PLANTILLA = [
  { id: 'kpis', etiqueta: 'Zona de KPIs', ids: ['kpi-1', 'kpi-2', 'kpi-3', 'kpi-4'] },
  { id: 'grafico-principal', etiqueta: 'Zona de gráfico principal', ids: ['grafico-3'] },
  { id: 'graficos-apoyo', etiqueta: 'Zona de gráficos de apoyo', ids: ['grafico-1', 'grafico-2', 'grafico-4', 'grafico-5', 'grafico-6'] },
  { id: 'tabla-principal', etiqueta: 'Zona de tabla principal', ids: ['tabla-1'] },
  { id: 'tablas-apoyo', etiqueta: 'Zona de tablas secundarias o de apoyo', ids: ['tabla-2', 'tabla-3'] },
  { id: 'tablas-historicas', etiqueta: 'Zona de tablas históricas', ids: ['tabla-4', 'tabla-5'] },
]
