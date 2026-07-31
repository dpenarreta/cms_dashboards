import { Alert, Form, Button, Table } from 'react-bootstrap'

/**
 * Paso "reconocer columnas y confirmar alias": el análisis automático es solo una sugerencia —
 * ninguna columna se quita ni se marca como no utilizable por sí sola, TODAS se muestran siempre.
 * El usuario decide con un checkmark cuál usar (precargado con la sugerencia del sistema) y puede
 * ponerle un alias — ese alias es el que después se usa para componer el título y la descripción
 * de las recomendaciones de gráficas (`utils/chartRecommendations.js`).
 */
export default function ColumnAliasStep({
  archivoInfo, columnas, aliases, utilizables, onActualizarAlias, onActualizarUtilizable, onContinuar, cargando, error,
}) {
  const etiquetaTipo = (tipo) => {
    if (tipo === 'numerico') return 'Numérica'
    if (tipo === 'fecha') return 'Fecha'
    if (tipo === 'vacio') return 'Vacía'
    return 'Categoría'
  }

  const haySeleccionadas = columnas.some((c) => utilizables[c.nombre])

  return (
    <div>
      {archivoInfo && (
        <p className="chart-panel__subtitle">
          Archivo: {archivoInfo.nombreArchivo} · {archivoInfo.totalFilas} fila(s) detectadas
        </p>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      <div className="chart-panel mb-3">
        <h6>Columnas detectadas</h6>
        <p className="chart-panel__subtitle">
          Marca cuáles columnas se pueden usar para generar gráficas (el sistema precarga una
          sugerencia, pero la decisión es tuya) y ponles un alias si quieres que se muestren con
          un nombre más claro. Por defecto el alias es el mismo nombre original.
        </p>

        {columnas.length === 0 ? (
          <Alert variant="warning" className="mb-0">No se detectaron columnas en el archivo.</Alert>
        ) : (
          <Table responsive size="sm">
            <thead>
              <tr>
                <th>Utilizable</th>
                <th>Columna</th>
                <th>Tipo</th>
                <th>Alias</th>
              </tr>
            </thead>
            <tbody>
              {columnas.map((c) => (
                <tr key={c.nombre}>
                  <td>
                    <Form.Check
                      type="checkbox"
                      checked={Boolean(utilizables[c.nombre])}
                      onChange={(e) => onActualizarUtilizable(c.nombre, e.target.checked)}
                      aria-label={`Utilizable: ${c.nombre}`}
                    />
                  </td>
                  <td>
                    {c.nombre}
                    {!utilizables[c.nombre] && c.motivo_no_apta && (
                      <div className="chart-panel__subtitle mb-0">Sugerencia: {c.motivo_no_apta}</div>
                    )}
                  </td>
                  <td>{etiquetaTipo(c.tipo)}</td>
                  <td>
                    <Form.Control
                      size="sm"
                      value={aliases[c.nombre] ?? c.nombre}
                      onChange={(e) => onActualizarAlias(c.nombre, e.target.value)}
                      aria-label={`Alias para ${c.nombre}`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <Button variant="primary" onClick={onContinuar} disabled={cargando || !haySeleccionadas}>
        {cargando ? 'Generando recomendaciones…' : 'Continuar'}
      </Button>
      {!haySeleccionadas && columnas.length > 0 && (
        <Alert variant="warning" className="mt-3 mb-0">
          Marca al menos una columna como utilizable para poder generar gráficas.
        </Alert>
      )}
    </div>
  )
}
