import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import * as brandingService from '../services/brandingService'

const ThemeContext = createContext(null)

const VARIABLES_CSS = {
  color_primary: '--color-primary',
  color_secondary: '--color-secondary',
  color_background: '--color-background',
  color_headings: '--color-headings',
  color_text: '--color-text',
  color_links: '--color-links',
  color_buttons: '--color-buttons',
  color_menu: '--color-menu',
  font_primary_css: '--font-primary',
  font_secondary_css: '--font-secondary',
  font_size_base: '--font-size-base',
  border_radius_css: '--border-radius',
}

// Colores semánticos que la app realmente usa vía `variant`/`bg` de react-bootstrap
// (`btn-primary`, `btn-outline-danger`, `badge bg-success`, etc. — ver grep de `variant=`/`bg=`
// en `frontend/src`).
const COLORES_SEMANTICOS = {
  color_primary: 'primary',
  color_secondary: 'secondary',
  color_success: 'success',
  color_danger: 'danger',
  color_warning: 'warning',
  color_info: 'info',
}

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/
const ID_ESTILOS_BOOTSTRAP = 'theme-bootstrap-overrides'

function hexANormalizado(hex) {
  return hex.length === 4 ? `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}` : hex
}

function hexARgb(hex) {
  const normalizado = hexANormalizado(hex)
  const canal = (inicio) => parseInt(normalizado.slice(inicio, inicio + 2), 16)
  return `${canal(1)}, ${canal(3)}, ${canal(5)}`
}

/** Oscurece un color hex ~20% (sin depender de `color-mix()` por compatibilidad de navegador,
 * misma alternativa seguida por el resto del proyecto — ver docs/frontend/bootstrap_theme.md). */
function oscurecer(hex, porcentaje = 0.2) {
  if (!HEX_RE.test(hex || '')) return hex
  const normalizado = hexANormalizado(hex)
  const canal = (inicio) => {
    const valor = parseInt(normalizado.slice(inicio, inicio + 2), 16)
    return Math.max(0, Math.round(valor * (1 - porcentaje)))
  }
  const aHex = (n) => n.toString(16).padStart(2, '0')
  return `#${aHex(canal(1))}${aHex(canal(3))}${aHex(canal(5))}`
}

/** Aclara un color hex mezclándolo hacia blanco (mismo cálculo directo por canal que
 * `oscurecer()`, sin `color-mix()`). Se usa para el fondo/borde tenues de `.alert-*`, imitando el
 * esquema "subtle/emphasis" que Bootstrap resuelve en Sass en tiempo de build. */
function aclarar(hex, porcentaje) {
  if (!HEX_RE.test(hex || '')) return hex
  const normalizado = hexANormalizado(hex)
  const canal = (inicio) => {
    const valor = parseInt(normalizado.slice(inicio, inicio + 2), 16)
    return Math.min(255, Math.round(valor + (255 - valor) * porcentaje))
  }
  const aHex = (n) => n.toString(16).padStart(2, '0')
  return `#${aHex(canal(1))}${aHex(canal(3))}${aHex(canal(5))}`
}

/**
 * Bootstrap 5.3, tal como viene precompilado en `bootstrap.min.css`, NO lee `--bs-primary` (u
 * otros nombres de esa forma) dentro de `.btn-primary`/`.btn-outline-primary` — esa clase fija
 * sus propias variables internas (`--bs-btn-bg`, `--bs-btn-border-color`, etc.) con el hexadecimal
 * de Sass ya resuelto en tiempo de build. Sobreescribir solo `--bs-primary` en `:root` no cambia
 * ningún botón (se verificó visualmente: el color no cambiaba). La única forma de reteñir estos
 * componentes sin recompilar Bootstrap es inyectar una regla CSS que redefina esas variables
 * internas directamente sobre la misma clase — eso es lo que hace esta función, generando una
 * hoja de estilos que se actualiza cada vez que cambia el tema institucional.
 */
function generarEstilosBootstrap(tema) {
  const bloques = []

  Object.entries(COLORES_SEMANTICOS).forEach(([campo, sufijo]) => {
    const color = tema[campo]
    if (!HEX_RE.test(color || '')) return
    const oscuro = oscurecer(color)
    const textoBoton = HEX_RE.test(tema.color_button_text || '') ? tema.color_button_text : '#ffffff'

    bloques.push(`.btn-${sufijo} {
      --bs-btn-bg: ${color}; --bs-btn-border-color: ${color};
      --bs-btn-hover-bg: ${oscuro}; --bs-btn-hover-border-color: ${oscuro};
      --bs-btn-active-bg: ${oscuro}; --bs-btn-active-border-color: ${oscuro};
      --bs-btn-disabled-bg: ${color}; --bs-btn-disabled-border-color: ${color};
      --bs-btn-color: ${textoBoton}; --bs-btn-hover-color: ${textoBoton};
      --bs-btn-active-color: ${textoBoton}; --bs-btn-disabled-color: ${textoBoton};
    }`)
    bloques.push(`.btn-outline-${sufijo} {
      --bs-btn-color: ${color}; --bs-btn-border-color: ${color};
      --bs-btn-hover-bg: ${color}; --bs-btn-hover-border-color: ${color}; --bs-btn-hover-color: ${textoBoton};
      --bs-btn-active-bg: ${color}; --bs-btn-active-border-color: ${color}; --bs-btn-active-color: ${textoBoton};
      --bs-btn-disabled-color: ${color}; --bs-btn-disabled-border-color: ${color};
    }`)
    // `!important`: Bootstrap ya declara `.bg-*`/`.text-*` con `!important` (utilidades) —
    // igualarlo es lo único que permite ganar el empate de especificidad.
    bloques.push(`.bg-${sufijo} { background-color: ${color} !important; }`)
    bloques.push(`.text-${sufijo} { color: ${color} !important; }`)
    // `.alert-*` (react-bootstrap <Alert variant="danger">, usado en toda la app para errores y
    // confirmaciones) tampoco lee `--bs-danger`: fija sus propias variables `--bs-alert-*` desde
    // colores "subtle/emphasis" resueltos por Sass. Se redefinen esas mismas variables aquí.
    bloques.push(`.alert-${sufijo} {
      --bs-alert-bg: ${aclarar(color, 0.85)}; --bs-alert-border-color: ${aclarar(color, 0.6)};
      --bs-alert-color: ${oscurecer(color, 0.15)}; --bs-alert-link-color: ${oscurecer(color, 0.15)};
    }`)
  })

  if (HEX_RE.test(tema.color_links || '')) {
    const hoverEnlaces = oscurecer(tema.color_links)
    bloques.push(`a, .btn-link { color: ${tema.color_links}; }`)
    bloques.push(`a:hover, .btn-link:hover { color: ${hoverEnlaces}; }`)
  }

  // Foco y controles seleccionados (casillas/switches): Bootstrap los ata al azul por defecto
  // (`#0d6efd`) igual que los botones — mismo problema, mismo patrón de solución.
  if (HEX_RE.test(tema.color_primary || '')) {
    const primario = tema.color_primary
    const rgb = hexARgb(primario)
    bloques.push(`.form-check-input:checked { background-color: ${primario}; border-color: ${primario}; }`)
    bloques.push(`.form-control:focus, .form-check-input:focus, .form-select:focus {
      border-color: ${primario}; box-shadow: 0 0 0 .25rem rgba(${rgb}, .25);
    }`)
  }

  return bloques.join('\n')
}

function aplicarEstilosBootstrap(tema) {
  let estilo = document.getElementById(ID_ESTILOS_BOOTSTRAP)
  if (!estilo) {
    estilo = document.createElement('style')
    estilo.id = ID_ESTILOS_BOOTSTRAP
    document.head.appendChild(estilo)
  }
  estilo.textContent = generarEstilosBootstrap(tema)
}

function aplicarTema(tema) {
  if (!tema) return
  const raiz = document.documentElement
  Object.entries(VARIABLES_CSS).forEach(([campo, variable]) => {
    if (tema[campo]) raiz.style.setProperty(variable, tema[campo])
  })
  aplicarEstilosBootstrap(tema)
  if (tema.site_name) document.title = tema.site_name
  if (tema.favicon_url) {
    let icono = document.querySelector('link[rel="icon"]')
    if (!icono) {
      icono = document.createElement('link')
      icono.rel = 'icon'
      document.head.appendChild(icono)
    }
    icono.href = tema.favicon_url
  }
}

/**
 * Identidad institucional consolidada (sección 16 de la integración con skelleton_base): login,
 * landing y panel autenticado leen todos de la misma fuente (`GET /api/branding/current`,
 * público — el login también debe verse con la marca configurada, sin sesión). Si la solicitud
 * falla o el valor de un campo viene vacío, se conservan los valores estáticos ya definidos en
 * `styles/dashboard.css` (fallback "de arranque en frío"), no se rompe la identidad visual.
 */
export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(null)

  const cargar = useCallback(() => {
    brandingService.getCurrent()
      .then((tema) => {
        setTheme(tema)
        aplicarTema(tema)
      })
      .catch(() => {
        // Sin tema del backend: se queda con los valores estáticos de dashboard.css.
      })
  }, [])

  useEffect(() => { cargar() }, [cargar])

  return <ThemeContext.Provider value={{ theme, reloadTheme: cargar }}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const contexto = useContext(ThemeContext)
  if (!contexto) throw new Error('useTheme debe usarse dentro de <ThemeProvider>.')
  return contexto
}
