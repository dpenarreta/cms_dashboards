import { useCallback, useEffect, useState } from 'react'

const CLAVE_ALMACENAMIENTO = 'tema-color-modo'

/** Aplica el modo claro/oscuro a todo el documento con los dos atributos que pide la identidad
 * base de la Matriz: `data-theme` cambia los tokens `--mz-*` (y, a través de `identidad-cms.css`,
 * las variables propias de este proyecto) y `data-bs-theme` cambia los campos, modales, tablas y
 * botones de Bootstrap 5.3. Hacen falta los dos siempre.
 *
 * No escribe ningún color en línea: los valores de cada modo viven en las hojas de estilo. Antes
 * se pisaba `--color-background` en línea porque la identidad institucional también lo escribía
 * en línea; desde que la base es la Matriz, la marca ya no toca fondos ni textos. */
function aplicarModo(oscuro) {
  const raiz = document.documentElement
  raiz.setAttribute('data-theme', oscuro ? 'dark' : 'light')
  raiz.setAttribute('data-bs-theme', oscuro ? 'dark' : 'light')
}

/** Alterna el modo claro/oscuro de toda la aplicación (botón de la barra superior,
 * `AdminLayout`) y lo recuerda en `localStorage`. */
export function useColorMode() {
  const [oscuro, setOscuro] = useState(() => localStorage.getItem(CLAVE_ALMACENAMIENTO) === '1')

  useEffect(() => {
    localStorage.setItem(CLAVE_ALMACENAMIENTO, oscuro ? '1' : '0')
    aplicarModo(oscuro)
  }, [oscuro])

  const alternar = useCallback(() => setOscuro((v) => !v), [])

  return { oscuro, alternar }
}
