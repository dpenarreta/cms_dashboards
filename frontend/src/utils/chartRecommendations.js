/**
 * Compone el título y la descripción visibles de una recomendación de gráfica a partir de los
 * alias que el usuario le puso a cada columna (o el nombre original si no le puso ninguno) —
 * usado tanto por el hook (para el título que se envía a `agregar-grafica`) como por el
 * componente de presentación (`ChartRecommendations`), para que ambos compongan el mismo texto.
 */
export function aliasDe(aliases, columna) {
  return aliases?.[columna] || columna
}

export function tituloRecomendacion(recomendacion, aliases) {
  if (recomendacion.tipo_grafica === 'dispersion') {
    return `${aliasDe(aliases, recomendacion.columna_valor)} vs. ${aliasDe(aliases, recomendacion.columna_valor_y)}`
  }
  return recomendacion.columna_categoria
    ? `${aliasDe(aliases, recomendacion.columna_valor)} por ${aliasDe(aliases, recomendacion.columna_categoria)}`
    : `Total de ${aliasDe(aliases, recomendacion.columna_valor)}`
}

/**
 * Texto libre; no describe una forma de dibujo concreta ("barras", "pastel"...) porque el usuario
 * puede visualizar la misma recomendación de cualquiera de las formas de `chartTypes.js` — este
 * mismo texto es el que se guarda como descripción editable del componente al agregarlo.
 */
export function descripcionRecomendacion(recomendacion, aliases) {
  if (recomendacion.tipo_grafica === 'kpi') {
    return `Suma de todos los valores de "${aliasDe(aliases, recomendacion.columna_valor)}".`
  }
  if (recomendacion.tipo_grafica === 'dispersion') {
    return `Relación entre "${aliasDe(aliases, recomendacion.columna_valor)}" y `
      + `"${aliasDe(aliases, recomendacion.columna_valor_y)}": cada punto es una fila del archivo.`
  }
  const categorias = recomendacion.categorias_unicas
  return `Suma de "${aliasDe(aliases, recomendacion.columna_valor)}" agrupada por `
    + `"${aliasDe(aliases, recomendacion.columna_categoria)}"${categorias ? ` (${categorias} categorías)` : ''}.`
}
