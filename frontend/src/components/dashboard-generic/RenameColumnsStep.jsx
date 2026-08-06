import { Alert, Button, Form, Table } from 'react-bootstrap'

function columnasFinales(columnas, aliases) {
  return columnas.map((c) => (aliases[c] || '').trim() || c)
}

function nombresDuplicados(finales) {
  return finales.filter((nombre, indice) => finales.indexOf(nombre) !== indice)
}

/** Columnas que ya estaban marcadas como históricas en una carga anterior de este dashboard
 * (`columnasHistoricasConfiguradas`, ver `ColumnaHistorica`) pero que no aparecen en este archivo
 * (ya renombrado) — si el usuario les cambió el nombre de más de la cuenta, o el archivo dejó de
 * traerlas, esta es la única señal de que se van a "perder" de la comparación histórica: al no
 * estar en la lista, ni siquiera tienen una fila con casilla para volver a tildarlas acá. */
function columnasHistoricasFaltantes(finales, columnasHistoricasConfiguradas) {
  return columnasHistoricasConfiguradas.filter((c) => !finales.includes(c))
}

/**
 * Paso "renombrar columnas": tras validar el archivo, se muestran TODAS sus columnas para que el
 * usuario les ponga un nombre más claro antes del mapeo a la plantilla — a la izquierda el nuevo
 * nombre (editable, precargado con el original), a la derecha la columna fuente tal como viene en
 * el archivo. Ninguna columna se excluye ni se marca como no utilizable acá; eso lo decide el
 * mapeo (`TemplateMappingStep`), que ya trabaja sobre los nombres renombrados.
 *
 * Cada fila tiene además una casilla "Histórica" (`columnasHistoricas`/`onCambiarColumnaHistorica`)
 * — las columnas tildadas quedan guardadas como configuración del dashboard
 * (`ColumnaHistorica`, backend) y alimentan automáticamente Tabla 4/Tabla 5 de ahí en más, sin
 * tener que elegir nada en el paso de Mapeo. `columnasHistoricasConfiguradas` (lo que ya estaba
 * tildado en una carga anterior) se usa solo para advertir si alguna de esas columnas no aparece
 * en este archivo (`columnasHistoricasFaltantes`) — no bloquea, es información para decidir.
 */
export default function RenameColumnsStep({
  archivoInfo, columnas, aliases, onActualizarAlias, onContinuar, onCancelar, cargando, error,
  columnasHistoricas = [], onCambiarColumnaHistorica, columnasHistoricasConfiguradas = [],
}) {
  const finales = columnasFinales(columnas, aliases)
  const duplicados = nombresDuplicados(finales)
  const hayDuplicados = duplicados.length > 0
  const faltantes = columnasHistoricasFaltantes(finales, columnasHistoricasConfiguradas)

  return (
    <div>
      {archivoInfo && (
        <p className="chart-panel__subtitle">
          Archivo: {archivoInfo.nombreArchivo} · {archivoInfo.totalFilas} fila(s) detectadas
        </p>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      <div className="chart-panel mb-3">
        <h6>Renombrar columnas</h6>
        <p className="chart-panel__subtitle">
          Ponle un nombre más claro a cualquier columna del archivo antes de armar la plantilla.
          Si no cambias algo, se usa el nombre original.
        </p>

        {columnas.length === 0 ? (
          <Alert variant="warning" className="mb-0">No se detectaron columnas en el archivo.</Alert>
        ) : (
          <Table responsive size="sm">
            <thead>
              <tr>
                <th>Nuevo nombre</th>
                <th>Columna en el archivo</th>
                <th>Histórica</th>
              </tr>
            </thead>
            <tbody>
              {columnas.map((nombre) => (
                <tr key={nombre}>
                  <td>
                    <Form.Control
                      size="sm"
                      value={aliases[nombre] ?? nombre}
                      onChange={(e) => onActualizarAlias(nombre, e.target.value)}
                      aria-label={`Nuevo nombre para ${nombre}`}
                    />
                  </td>
                  <td className="chart-panel__subtitle mb-0">{nombre}</td>
                  <td>
                    <Form.Check
                      type="checkbox"
                      checked={columnasHistoricas.includes(nombre)}
                      onChange={(e) => onCambiarColumnaHistorica(nombre, e.target.checked)}
                      aria-label={`Marcar "${nombre}" como columna histórica`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      {hayDuplicados && (
        <Alert variant="danger">
          Hay columnas con el mismo nuevo nombre ({[...new Set(duplicados)].join(', ')}). Cambia
          alguna para poder continuar.
        </Alert>
      )}

      {faltantes.length > 0 && (
        <Alert variant="warning">
          Estas columnas estaban marcadas como históricas y no están en este archivo:{' '}
          {faltantes.map((c) => `"${c}"`).join(', ')}. Si les cambiaste el nombre, revisalo antes
          de continuar; si de verdad ya no vienen, van a dejar de actualizarse en la comparación
          histórica a partir de esta carga.
        </Alert>
      )}

      <div className="d-flex gap-2">
        <Button variant="primary" onClick={onContinuar} disabled={cargando || hayDuplicados}>
          {cargando ? 'Analizando…' : 'Continuar'}
        </Button>
        <Button variant="outline-secondary" onClick={onCancelar} disabled={cargando}>Cancelar</Button>
      </div>
    </div>
  )
}
