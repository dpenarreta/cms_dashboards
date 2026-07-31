import { useState } from 'react'
import { Alert, Badge, Button, Form } from 'react-bootstrap'
import { descripcionRecomendacion, tituloRecomendacion } from '../../utils/chartRecommendations'
import { TIPOS_VISUALIZACION, tiposDisponiblesPara } from '../../utils/chartTypes'
import GenericChartRenderer from './GenericChartRenderer'

function tipoPorDefecto(recomendacion) {
  if (recomendacion.tipo_grafica === 'dispersion') return 'dispersion'
  return recomendacion.columna_categoria ? 'barras_horizontales' : 'kpi'
}

/**
 * Paso "recomendaciones de gráficas": cada tarjeta propone qué información mostraría (compuesto a
 * partir de los alias del paso anterior) y, salvo los totales simples, un selector con todas las
 * formas de visualización disponibles para esa combinación de columnas (tarjeta KPI, barras
 * verticales/horizontales/agrupadas/apiladas, líneas, pastel, dona, tabla —
 * `utils/chartTypes.js`). "Vista previa" renderiza la elección actual con los datos ya calculados
 * por el backend (`recomendacion.datos`/`datos_multiserie`) — no hace falta agregarla primero
 * para ver cómo se vería. "Agregar" incluye la gráfica en el dashboard de inmediato, con la
 * visualización elegida, sin un paso final de "generar" aparte.
 */
export default function ChartRecommendations({
  recomendaciones, aliases, agregadas, onAgregar, onVolver, onFinalizar, cargando, error,
}) {
  const [previsualizando, setPrevisualizando] = useState(() => new Set())
  const [tiposSeleccionados, setTiposSeleccionados] = useState({})
  const hayAgregadas = agregadas.size > 0

  const alternarVistaPrevia = (id) => {
    setPrevisualizando((prev) => {
      const siguiente = new Set(prev)
      if (siguiente.has(id)) siguiente.delete(id)
      else siguiente.add(id)
      return siguiente
    })
  }

  const tipoSeleccionado = (r) => tiposSeleccionados[r.id] || tipoPorDefecto(r)
  const cambiarTipo = (id, tipo) => setTiposSeleccionados((prev) => ({ ...prev, [id]: tipo }))

  return (
    <div>
      {error && <Alert variant="danger">{error}</Alert>}
      <div className="d-flex justify-content-between align-items-start flex-wrap gap-2">
        <p className="chart-panel__subtitle">
          Estas son las gráficas que recomendamos según las columnas del archivo. Elige cómo
          visualizar cada una y agrega las que te sirvan.
        </p>
        <Button variant="outline-secondary" size="sm" onClick={onVolver} disabled={cargando}>
          Volver a las columnas
        </Button>
      </div>

      {recomendaciones.length === 0 && (
        <Alert variant="warning">No se generaron recomendaciones para este archivo.</Alert>
      )}

      <div className="d-flex flex-column gap-2 mb-3">
        {recomendaciones.map((r) => {
          const agregada = agregadas.has(r.id)
          const mostrarPreview = previsualizando.has(r.id)
          const titulo = tituloRecomendacion(r, aliases)
          const tipo = tipoSeleccionado(r)
          const tipoInfo = TIPOS_VISUALIZACION.find((t) => t.id === tipo)
          const opciones = tiposDisponiblesPara(r)
          const datosListos = tipoInfo?.requiereSerie ? r.datos_multiserie : r.datos

          return (
            <div key={r.id} className="chart-panel">
              <div className="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <Badge bg={tipo === 'kpi' ? 'secondary' : 'primary'}>{tipoInfo?.etiqueta}</Badge>
                    <strong>{titulo}</strong>
                  </div>
                  <div className="chart-panel__subtitle mb-0">{descripcionRecomendacion(r, aliases)}</div>
                </div>
                <div className="d-flex align-items-center gap-2 flex-wrap">
                  {opciones.length > 1 && (
                    <Form.Select
                      size="sm"
                      style={{ width: 'auto' }}
                      value={tipo}
                      onChange={(e) => cambiarTipo(r.id, e.target.value)}
                      disabled={agregada}
                      aria-label={`Tipo de visualización para ${titulo}`}
                    >
                      {opciones.map((o) => <option key={o.id} value={o.id}>{o.etiqueta}</option>)}
                    </Form.Select>
                  )}
                  <Button size="sm" variant="outline-secondary" onClick={() => alternarVistaPrevia(r.id)}>
                    {mostrarPreview ? 'Ocultar vista previa' : 'Vista previa'}
                  </Button>
                  <Button
                    size="sm"
                    variant={agregada ? 'outline-secondary' : 'primary'}
                    disabled={agregada || cargando}
                    onClick={() => onAgregar(r, tipo)}
                  >
                    {agregada ? 'Agregada ✓' : 'Agregar'}
                  </Button>
                </div>
              </div>

              {mostrarPreview && (
                <div className="mt-3" style={{ maxWidth: tipo === 'kpi' ? 260 : '100%' }}>
                  {datosListos ? (
                    <GenericChartRenderer
                      tipoVisualizacion={tipo}
                      datos={r.datos}
                      datosMultiserie={r.datos_multiserie}
                      titulo={titulo}
                    />
                  ) : (
                    <Alert variant="secondary" className="mb-0 py-2">Vista previa no disponible.</Alert>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <Button variant="primary" onClick={onFinalizar} disabled={!hayAgregadas}>
        Ir al dashboard
      </Button>
    </div>
  )
}
