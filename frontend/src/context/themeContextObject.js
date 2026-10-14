import { createContext } from 'react'

/** El objeto de contexto de la identidad institucional, aparte de `ThemeContext.jsx` para que
 * `hooks/useMarca.js` pueda leerlo sin que ese archivo exporte algo más que componentes (Fast
 * Refresh). Lo provee `ThemeProvider`. */
export const ThemeContext = createContext(null)
