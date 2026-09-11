/**
 * Bloques de texto compartidos por las secciones del Dashboard Directorio.
 *
 * Solo componentes: el formato de números vive en `formato.js` (ver el motivo allí).
 */

/** Interpreta los `**dobles asteriscos**` como negrita, igual criterio que `HallazgosClaveCard`. */
function conNegritas(texto) {
  return texto.split(/(\*\*[^*]+\*\*)/g).map((parte, i) => (
    parte.startsWith('**') && parte.endsWith('**')
      // eslint-disable-next-line react/no-array-index-key -- el índice ES la identidad del fragmento
      ? <strong key={i}>{parte.slice(2, -2)}</strong>
      // eslint-disable-next-line react/no-array-index-key -- ídem
      : <span key={i}>{parte}</span>
  ))
}

/** El bloque "HALLAZGOS CLAVE" del informe: barra lateral, título y párrafo. */
export function HallazgosClave({ texto }) {
  if (!texto) return null
  return (
    <div className="directorio-hallazgos">
      <div className="directorio-hallazgos__titulo">📊 HALLAZGOS CLAVE</div>
      <p className="directorio-hallazgos__texto">{conNegritas(texto)}</p>
    </div>
  )
}

/** Las notas al pie en cursiva que el informe pone bajo varias secciones. */
export function Nota({ texto }) {
  if (!texto) return null
  return <p className="directorio-nota">{texto}</p>
}

export function TituloSeccion({ children }) {
  return <div className="directorio-seccion__titulo">{children}</div>
}
