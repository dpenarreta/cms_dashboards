/**
 * Espejo de `cartera/services/generic_charts.py::TIPOS_VISUALIZACION` — los mismos ids se usan
 * como `tipo_visualizacion` al agregar una gráfica y como `chart_type` del componente persistido.
 * `requiereCategoria`/`requiereSerie` deciden qué opciones se pueden ofrecer para cada
 * recomendación (una sin columna de categoría solo puede verse como KPI; una sin
 * `columna_serie_sugerida` no puede verse como barras agrupadas/apiladas).
 */
export const TIPOS_VISUALIZACION = [
  { id: 'kpi', etiqueta: 'Tarjeta KPI', requiereCategoria: false, requiereSerie: false },
  { id: 'barras_horizontales', etiqueta: 'Barras horizontales', requiereCategoria: true, requiereSerie: false },
  { id: 'barras_verticales', etiqueta: 'Barras verticales', requiereCategoria: true, requiereSerie: false },
  { id: 'barras_agrupadas', etiqueta: 'Barras agrupadas', requiereCategoria: true, requiereSerie: true },
  { id: 'barras_apiladas', etiqueta: 'Barras apiladas', requiereCategoria: true, requiereSerie: true },
  { id: 'area_apilada', etiqueta: 'Área apilada', requiereCategoria: true, requiereSerie: true },
  { id: 'lineas', etiqueta: 'Líneas', requiereCategoria: true, requiereSerie: false },
  { id: 'pastel', etiqueta: 'Pastel', requiereCategoria: true, requiereSerie: false },
  { id: 'dona', etiqueta: 'Dona', requiereCategoria: true, requiereSerie: false },
  { id: 'tabla', etiqueta: 'Tabla', requiereCategoria: true, requiereSerie: false },
  // A diferencia del resto, no agrupa por categoría: plots pares (x, y) de dos columnas
  // numéricas. Solo aparece en su propia recomendación (`tipo_grafica === 'dispersion'`), nunca
  // como variante de una recomendación con categoría — por eso no participa del filtro genérico
  // de `tiposDisponiblesPara` de abajo.
  { id: 'dispersion', etiqueta: 'Dispersión', requiereCategoria: false, requiereSerie: false },
]

/**
 * Tipos de visualización disponibles para una recomendación concreta: una de dispersión
 * (`tipo_grafica === 'dispersion'`) solo puede verse de esa única forma (no tiene sentido como
 * barras/pastel — son pares de valores, no una categoría agrupada). Si no tiene columna de
 * categoría (es un total simple, `datos = {valor}`) solo puede verse como KPI — no hay
 * categorías/valores que dibujar como barras/línea/pastel/tabla. Si tiene categoría, puede verse
 * en cualquiera de las formas de una sola serie, y además como barras agrupadas/apiladas o área
 * apilada cuando el backend encontró una segunda columna de agrupación
 * (`columna_serie_sugerida`).
 */
export function tiposDisponiblesPara(recomendacion) {
  if (recomendacion.tipo_grafica === 'dispersion') return TIPOS_VISUALIZACION.filter((t) => t.id === 'dispersion')
  if (!recomendacion.columna_categoria) return TIPOS_VISUALIZACION.filter((t) => t.id === 'kpi')
  return TIPOS_VISUALIZACION.filter((t) => (
    t.id !== 'kpi' && t.id !== 'dispersion' && (!t.requiereSerie || Boolean(recomendacion.columna_serie_sugerida))
  ))
}
