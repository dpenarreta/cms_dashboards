import { useId, useState } from 'react'
import { Collapse } from 'react-bootstrap'
import { generarHallazgos } from '../../utils/hallazgosClave'

/** Interpreta los `**dobles asteriscos**` que `generarHallazgos` usa para resaltar los números y
 * nombres importantes del párrafo, como negrita real — el mismo texto siempre se parte en la
 * misma cantidad de segmentos, alternando normal/negrita, así que el índice alcanza como key. */
function renderConNegritas(texto) {
  return texto.split('**').map((parte, i) => (
    i % 2 === 1
      // eslint-disable-next-line react/no-array-index-key -- segmentos de un mismo texto generado, sin id propio
      ? <strong key={i}>{parte}</strong>
      // eslint-disable-next-line react/no-array-index-key -- ídem
      : <span key={i}>{parte}</span>
  ))
}

/**
 * Recuadro "Hallazgos clave" (sección 25/26/27) al pie de cada KPI/gráfico/tabla del dashboard: un
 * párrafo con la interpretación de esa posición, recalculado en cada render a partir de los
 * mismos `datos`/`datosMultiserie` que el propio componente usa para dibujarse
 * (`generarHallazgos`) — así cambiar el tipo de gráfico, las columnas mapeadas o el archivo
 * cambia también la redacción, sin un paso aparte que la deje desactualizada. El encabezado es un
 * botón que expande/contrae el párrafo (tipo "collapse", empieza expandido) — cada posición del
 * dashboard tiene su propio estado, independiente del resto. Si no hay datos suficientes para
 * decir algo (posición vacía), no se muestra nada.
 */
export default function HallazgosClaveCard({ variante, datos, datosMultiserie }) {
  const idContenido = useId()
  const [expandido, setExpandido] = useState(true)
  const texto = generarHallazgos(variante, { datos, datosMultiserie })
  if (!texto) return null

  return (
    <div className="hallazgos-clave">
      <button
        type="button"
        className="hallazgos-clave__titulo"
        onClick={() => setExpandido((v) => !v)}
        aria-expanded={expandido}
        aria-controls={idContenido}
      >
        <span>💡 Hallazgos clave</span>
        <span aria-hidden="true">{expandido ? '▲' : '▼'}</span>
      </button>
      <Collapse in={expandido}>
        <div id={idContenido}>
          <p className="hallazgos-clave__texto">{renderConNegritas(texto)}</p>
        </div>
      </Collapse>
    </div>
  )
}
