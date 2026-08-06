import { useCallback, useEffect, useState } from 'react'
import { useTheme } from '../context/ThemeContext'

const CLAVE_ALMACENAMIENTO = 'tema-color-modo'
const COLOR_FONDO_OSCURO = '#10141b'

/** Aplica el modo claro/oscuro a todo el documento: `data-theme` (variables propias de
 * `dashboard.css`, ver `:root[data-theme="dark"]`) y `data-bs-theme` (soporte nativo de
 * Bootstrap 5.3 para modales/offcanvas/formularios/tablas — así "toda la página" se retiñe sin
 * tener que redefinir cada componente de Bootstrap a mano). `--color-background` es la única
 * variable que también pertenece a la identidad institucional (`ThemeContext.jsx::aplicarTema`,
 * `apps.branding`) — se sobreescribe en línea acá, con el mismo mecanismo, porque un estilo en
 * línea siempre gana sobre cualquier regla de hoja de estilos (la de `dashboard.css` no alcanza
 * por sí sola una vez que la identidad institucional ya escribió la suya). */
function aplicarModo(oscuro) {
  const raiz = document.documentElement
  raiz.setAttribute('data-theme', oscuro ? 'dark' : 'light')
  raiz.setAttribute('data-bs-theme', oscuro ? 'dark' : 'light')
  if (oscuro) raiz.style.setProperty('--color-background', COLOR_FONDO_OSCURO)
  else raiz.style.removeProperty('--color-background')
}

/**
 * Alterna el modo claro/oscuro de toda la aplicación (botón en `AdminSidebar`) — persiste en
 * `localStorage`, mismo patrón ya usado por el colapso del propio menú. Depende de `useTheme()`
 * únicamente para volver a aplicar el modo oscuro cada vez que la identidad institucional
 * (`ThemeProvider`) (re)carga: esa carga es asincrónica y escribe `--color-background` en línea
 * sobre el mismo elemento — sin esta dependencia, un usuario que vuelve con el modo oscuro ya
 * guardado vería el fondo institucional (claro) "ganarle" al oscuro apenas termina de cargar el
 * tema de marca, porque esa carga sucede después del primer render de este hook.
 */
export function useColorMode() {
  const { theme } = useTheme()
  const [oscuro, setOscuro] = useState(() => localStorage.getItem(CLAVE_ALMACENAMIENTO) === '1')

  useEffect(() => {
    localStorage.setItem(CLAVE_ALMACENAMIENTO, oscuro ? '1' : '0')
    aplicarModo(oscuro)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `theme` es deliberado, ver docstring: reaplica el modo oscuro cada vez que la identidad institucional (re)carga
  }, [oscuro, theme])

  const alternar = useCallback(() => setOscuro((v) => !v), [])

  return { oscuro, alternar }
}
