/**
 * Formato de números del Dashboard Directorio.
 *
 * Vive separado de `comunes.jsx` porque un archivo que exporta componentes y además funciones
 * sueltas dispara `react(only-export-components)`: obliga a Vite a recargar la página entera al
 * editarlo en vez de intercambiar en caliente solo el componente. Mismo criterio que
 * `dashboard-generic/pieChartData.js`.
 *
 * Este dashboard replica una pestaña de un informe financiero impreso, así que usa el formato de
 * ese informe (`$3,388,555`: miles con coma, sin decimales) y no el `es-EC` del resto de la
 * aplicación (`$ 3.388.555,00`). Es deliberado y está acotado acá: `utils/format.js` sigue intacto
 * para todos los demás dashboards.
 */

/** `$3,388,555` — el formato del informe. */
export function moneda(valor) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return '—'
  return `$${Math.round(valor).toLocaleString('en-US')}`
}

/** `62%` / `12.64%`, según los decimales que pida la sección. */
export function porcentaje(valor, decimales = 0) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return '—'
  return `${valor.toFixed(decimales)}%`
}

/** `$2116K` — miles con K, sin decimales ni separador, como los ejes y etiquetas del informe. */
export function compacto(valor) {
  if (valor === null || valor === undefined || Number.isNaN(valor)) return '—'
  return `$${Math.round(valor / 1000)}K`
}
