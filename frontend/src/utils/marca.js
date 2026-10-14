/** Nombre que se muestra mientras la identidad institucional no cargó (o no tiene nombre). */
export const NOMBRE_SITIO_POR_DEFECTO = 'Dashboard de Cartera'

/** Logotipo de texto (`mz-glyph`) cuando la identidad institucional no tiene logo: dos letras, como
 * el `MA` de la Matriz (con tres no entran en el recuadro de 32px). Salen del nombre corto si lo
 * hay, o de las iniciales de las dos primeras palabras del nombre. Lo comparten el menú lateral, la
 * pantalla de acceso y la landing, para que la marca sea la misma en las tres. */
export function inicialesDeMarca(theme, nombre = theme?.site_name || NOMBRE_SITIO_POR_DEFECTO) {
  if (theme?.short_name) return theme.short_name.slice(0, 2).toUpperCase()
  return nombre.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase()
}
