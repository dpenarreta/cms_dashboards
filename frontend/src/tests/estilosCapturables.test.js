import { describe, expect, it } from 'vitest'
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * "Imprimir como PDF" captura el dashboard con html2canvas (`utils/pdfExport.js`), que reimplementa
 * su propio parser de CSS y NO entiende las funciones de color modernas. Cuando encuentra una,
 * lanza `Attempting to parse an unsupported color function "color"` y la exportación falla entera:
 * el dashboard se ve perfecto en pantalla y el PDF no sale nunca, sin ninguna pista visible.
 *
 * Ya pasó una vez, con `color-mix(in srgb, var(--color-primary) 7%, transparent)` en
 * `.directorio-hallazgos` — Chrome computa esa mezcla como `color(srgb …)`. Esta prueba existe para
 * que la próxima vez se note acá y no en producción.
 *
 * La alternativa es calcular la mezcla por canal, que es lo que ya hace `ThemeContext.jsx`
 * (`oscurecer`/`aclarar`/`hexARgb`), y pedir el color con `rgba(var(--color-primary-rgb), …)`.
 */

// `process.cwd()` y no `import.meta.url`: Vitest sirve los módulos por HTTP, así que
// `import.meta.url` acá no es una ruta de disco. El runner corre desde `frontend/`.
const DIRECTORIO = join(process.cwd(), 'src', 'styles')
const FUNCIONES_NO_CAPTURABLES = /\b(color-mix|oklch|oklab|lch|lab)\s*\(/

function hojasDeEstilo() {
  return readdirSync(DIRECTORIO).filter((n) => n.endsWith('.css'))
}

// Los comentarios se borran sobre el archivo ENTERO (son multilínea) reemplazando cada carácter
// por un espacio: así el texto explicativo —que nombra `color-mix()` justamente para decir por qué
// no se usa— no cuenta como infracción, pero los números de línea siguen siendo los reales.
function sinComentarios(css) {
  return css.replace(/\/\*[\s\S]*?\*\//g, (bloque) => bloque.replace(/[^\n]/g, ' '))
}

describe('hojas de estilo propias', () => {
  it('no usan funciones de color que html2canvas no sabe parsear', () => {
    const infractores = []
    for (const nombre of hojasDeEstilo()) {
      const css = readFileSync(join(DIRECTORIO, nombre), 'utf8')
      const lineasOriginales = css.split('\n')
      sinComentarios(css).split('\n').forEach((linea, i) => {
        if (FUNCIONES_NO_CAPTURABLES.test(linea)) {
          infractores.push(`${nombre}:${i + 1} → ${lineasOriginales[i].trim()}`)
        }
      })
    }
    expect(infractores, 'rompen "Imprimir como PDF" (ver el encabezado de este archivo)').toEqual([])
  })

  it('encuentra las hojas de estilo que dice revisar', () => {
    // Sin esto, un cambio de ruta dejaría la prueba de arriba verificando una lista vacía.
    expect(hojasDeEstilo().length).toBeGreaterThan(0)
  })
})
