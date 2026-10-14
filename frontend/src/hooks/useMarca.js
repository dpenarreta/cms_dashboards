import { useContext } from 'react'
import { ThemeContext } from '../context/themeContextObject'

/** La identidad institucional, o `null` si no cargó o no hay `ThemeProvider` arriba. Para las
 * pantallas que solo MUESTRAN la marca y también se montan sueltas (acceso, errores, pruebas):
 * a diferencia de `useTheme`, no lanza. */
export function useMarca() {
  return useContext(ThemeContext)?.theme ?? null
}
