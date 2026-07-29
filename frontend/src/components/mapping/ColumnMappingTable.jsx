import { useState } from 'react'
import { Alert, Badge, Button, Form, Spinner, Table } from 'react-bootstrap'
import { formatNumber } from '../../utils/format'

function FilaMapeo({ campo, columnaConfirmada, columnasDisponibles, onCambiar, obligatorio }) {
  const encontrada = Boolean(columnaConfirmada)
  return (
    <tr>
      <td>{campo.etiqueta}{obligatorio && <span className="text-danger"> *</span>}</td>
      <td>
        <Form.Select
          size="sm"
          value={columnaConfirmada || ''}
          onChange={(e) => onCambiar(campo.campo, e.target.value)}
          aria-label={`Columna para ${campo.etiqueta}`}
        >
          <option value="">— Sin asignar —</option>
          {columnasDisponibles.map((col) => (
            <option key={col} value={col}>{col}</option>
          ))}
        </Form.Select>
      </td>
      <td>
        <Badge bg={encontrada ? 'success' : 'danger'}>
          {encontrada ? 'Encontrada' : 'No encontrada'}
        </Badge>
      </td>
    </tr>
  )
}

export default function ColumnMappingTable({
  archivoInfo, mapeoSugerido, mapeoConfirmado, onActualizarMapeo, previewFilas,
  onProcesar, onLimpiar, onCambiarHoja, cargando, error, fechaCorte, onCambiarFechaCorte,
}) {
  const [mostrarOpcionales, setMostrarOpcionales] = useState(false)

  if (!mapeoSugerido) return null

  const faltantes = mapeoSugerido.obligatorios.filter((c) => !mapeoConfirmado[c.campo])
  const puedeProcesar = faltantes.length === 0 && !cargando

  return (
    <div>
      <div className="d-flex flex-wrap gap-4 mb-3">
        <div><strong>Archivo:</strong> {archivoInfo.nombreArchivo}</div>
        <div><strong>Tamaño:</strong> {(archivoInfo.tamanoBytes / 1024).toFixed(1)} KB</div>
        <div><strong>Filas detectadas:</strong> {formatNumber(archivoInfo.totalFilas)}</div>
        <div>
          <strong>Hoja:</strong>{' '}
          {archivoInfo.hojasDisponibles.length > 1 ? (
            <Form.Select
              size="sm"
              style={{ display: 'inline-block', width: 'auto' }}
              value={archivoInfo.hojaSeleccionada}
              onChange={(e) => onCambiarHoja(e.target.value)}
            >
              {archivoInfo.hojasDisponibles.map((h) => <option key={h} value={h}>{h}</option>)}
            </Form.Select>
          ) : archivoInfo.hojaSeleccionada}
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      <Form.Group className="mb-3" style={{ maxWidth: 260 }}>
        <Form.Label className="mb-1">Fecha de corte</Form.Label>
        <Form.Control
          type="date"
          value={fechaCorte || ''}
          onChange={(e) => onCambiarFechaCorte(e.target.value)}
        />
      </Form.Group>

      {faltantes.length > 0 && (
        <Alert variant="warning">
          Faltan columnas obligatorias por asignar: {faltantes.map((f) => f.etiqueta).join(', ')}.
        </Alert>
      )}

      <h6>Mapeo de columnas obligatorias</h6>
      <div className="table-scroll mb-3">
        <Table size="sm" bordered>
          <thead>
            <tr>
              <th>Campo del sistema</th>
              <th>Columna detectada</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {mapeoSugerido.obligatorios.map((campo) => (
              <FilaMapeo
                key={campo.campo}
                campo={campo}
                columnaConfirmada={mapeoConfirmado[campo.campo]}
                columnasDisponibles={mapeoSugerido.columnas_disponibles}
                onCambiar={onActualizarMapeo}
                obligatorio
              />
            ))}
          </tbody>
        </Table>
      </div>

      <Button variant="link" className="ps-0 mb-2" onClick={() => setMostrarOpcionales((v) => !v)}>
        {mostrarOpcionales ? 'Ocultar' : 'Mostrar'} columnas opcionales ({mapeoSugerido.opcionales.length})
      </Button>
      {mostrarOpcionales && (
        <div className="table-scroll mb-3">
          <Table size="sm" bordered>
            <thead>
              <tr>
                <th>Campo del sistema</th>
                <th>Columna detectada</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {mapeoSugerido.opcionales.map((campo) => (
                <FilaMapeo
                  key={campo.campo}
                  campo={campo}
                  columnaConfirmada={mapeoConfirmado[campo.campo]}
                  columnasDisponibles={mapeoSugerido.columnas_disponibles}
                  onCambiar={onActualizarMapeo}
                  obligatorio={false}
                />
              ))}
            </tbody>
          </Table>
        </div>
      )}

      {previewFilas?.length > 0 && (
        <>
          <h6>Vista previa ({previewFilas.length} primeras filas)</h6>
          <div className="table-scroll mb-3" style={{ maxHeight: 260 }}>
            <Table size="sm" striped bordered>
              <thead>
                <tr>
                  {mapeoSugerido.columnas_disponibles.map((col) => <th key={col}>{col}</th>)}
                </tr>
              </thead>
              <tbody>
                {previewFilas.map((fila, i) => (
                  <tr key={i}>
                    {mapeoSugerido.columnas_disponibles.map((col) => (
                      <td key={col}>{fila[col] === null || fila[col] === undefined ? '' : String(fila[col])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </>
      )}

      <div className="d-flex gap-2">
        <Button variant="success" disabled={!puedeProcesar} onClick={onProcesar}>
          {cargando ? <Spinner size="sm" animation="border" className="me-2" /> : null}
          Procesar dashboard
        </Button>
        <Button variant="outline-secondary" onClick={onLimpiar} disabled={cargando}>Limpiar</Button>
      </div>
    </div>
  )
}
