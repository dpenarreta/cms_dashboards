import { useState } from 'react'
import { Alert, Button, Form, Spinner, Table } from 'react-bootstrap'
import Pagination from '../common/Pagination'
import * as carteraService from '../../services/carteraService'
import { useDetalleCartera } from '../../hooks/useDetalleCartera'
import { formatCurrency, formatDate } from '../../utils/format'
import { PAGE_SIZES_PERMITIDOS } from '../../config/pageSizes'

const COLUMNAS = [
  { campo: 'cliente', etiqueta: 'Cliente' },
  { campo: 'ruc_cliente', etiqueta: 'RUC' },
  { campo: 'numero_documento', etiqueta: 'Documento' },
  { campo: 'fecha_emision', etiqueta: 'Emisión' },
  { campo: 'fecha_vencimiento', etiqueta: 'Vencimiento' },
  { campo: 'dias_vencidos', etiqueta: 'Días vencidos' },
  { campo: 'saldo', etiqueta: 'Saldo' },
  { campo: 'ciudad', etiqueta: 'Ciudad' },
  { campo: 'recuperador', etiqueta: 'Recuperador' },
  { campo: 'causal', etiqueta: 'Causal' },
  { campo: 'estado_calculado', etiqueta: 'Estado' },
  { campo: 'rango_mora', etiqueta: 'Rango de mora' },
]

/**
 * Tabla de detalle paginada. La usan tanto la sección principal del dashboard como el panel
 * de drill-down (`PortfolioDetailPanel`): ambas le pasan `cargaId`/`filtros`/`fechaCorte` y el
 * componente resuelve por sí mismo la consulta, orden, búsqueda y paginación vía
 * `useDetalleCartera`, para no duplicar esa lógica en cada lugar donde se muestra un detalle.
 */
export default function DetalleTable({ cargaId, filtros, fechaCorte, resumenValidacion, titulo = 'Detalle de documentos', override }) {
  titulo = override?.titulo || titulo
  const allowedPageSizes = override?.config?.allowedPageSizes || PAGE_SIZES_PERMITIDOS
  const {
    detalle, pagina, pageSize, orden, busqueda, cargando, error,
    irAPagina, setOrden, setBusqueda, actualizar, cambiarPageSize,
  } = useDetalleCartera({ cargaId, filtros, fechaCorte, pageSizeInicial: override?.config?.defaultPageSize ?? 10 })
  const [busquedaVisible, setBusquedaVisible] = useState(false)

  const contraerBusqueda = () => {
    setBusquedaVisible(false)
    setBusqueda('')
  }

  const pageSizeAplicado = detalle?.page_size || pageSize
  const totalPaginas = Math.max(Math.ceil((detalle?.count || 0) / pageSizeAplicado), 1)
  const paramsExport = { ...filtros, fecha_corte: fechaCorte, ordering: orden, buscar: busqueda }

  return (
    <div className="chart-panel">
      <div className="d-flex justify-content-between flex-wrap gap-2 mb-2">
        <div className="chart-panel__title mb-0">{titulo}</div>
        <div className="d-flex gap-2">
          <Button size="sm" variant="outline-secondary" onClick={actualizar} disabled={cargando}>Actualizar</Button>
          <a className="btn btn-sm btn-outline-primary" href={carteraService.urlExportar(cargaId, { ...paramsExport, formato: 'xlsx' })}>
            Exportar Excel
          </a>
          <a className="btn btn-sm btn-outline-primary" href={carteraService.urlExportar(cargaId, { ...paramsExport, formato: 'csv' })}>
            Exportar CSV
          </a>
          {resumenValidacion?.filas_descartadas > 0 && (
            <a className="btn btn-sm btn-outline-danger" href={carteraService.urlExportar(cargaId, { tipo: 'errores', formato: 'xlsx' })}>
              Descargar filas con error
            </a>
          )}
        </div>
      </div>

      <div className="d-flex align-items-center gap-2 mb-2">
        {busquedaVisible ? (
          <>
            <Form.Control
              size="sm"
              style={{ maxWidth: 320 }}
              placeholder="Buscar por cliente, RUC o documento..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              autoFocus
            />
            <Button
              size="sm"
              variant="outline-secondary"
              onClick={contraerBusqueda}
              aria-label="Contraer buscador"
              title="Contraer buscador"
            >
              ✕
            </Button>
          </>
        ) : (
          <Button
            size="sm"
            variant="outline-secondary"
            onClick={() => setBusquedaVisible(true)}
            aria-label="Mostrar buscador"
            title="Buscar"
          >
            🔍 Buscar
          </Button>
        )}
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      {cargando && (
        <div className="text-center py-4" role="status" aria-live="polite">
          <Spinner animation="border" size="sm" className="me-2" /> Cargando...
        </div>
      )}

      {!cargando && !error && (detalle?.results?.length ?? 0) === 0 && (
        <div className="text-center py-4 chart-panel__subtitle" role="status">
          No hay registros que cumplan los filtros aplicados.
        </div>
      )}

      {!cargando && !error && (detalle?.results?.length ?? 0) > 0 && (
        <div className="table-scroll">
          <Table size="sm" striped bordered hover>
            <thead>
              <tr>
                {COLUMNAS.map((c) => (
                  <th
                    key={c.campo}
                    role="button"
                    tabIndex={0}
                    onClick={() => setOrden(c.campo)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOrden(c.campo) } }}
                  >
                    {c.etiqueta}
                    {orden.replace('-', '') === c.campo ? (orden.startsWith('-') ? ' ▼' : ' ▲') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {detalle.results.map((fila) => (
                <tr key={`${fila.numero_documento}-${fila.ruc_cliente}`}>
                  <td>{fila.cliente}</td>
                  <td>{fila.ruc_cliente}</td>
                  <td>{fila.numero_documento}</td>
                  <td>{formatDate(fila.fecha_emision)}</td>
                  <td>{formatDate(fila.fecha_vencimiento)}</td>
                  <td>{fila.dias_vencidos ?? '—'}</td>
                  <td>{formatCurrency(fila.saldo)}</td>
                  <td>{fila.ciudad}</td>
                  <td>{fila.recuperador}</td>
                  <td>{fila.causal}</td>
                  <td>{fila.estado_calculado}</td>
                  <td>{fila.rango_mora}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}

      <Pagination
        idBase="detalle"
        paginaActual={pagina}
        totalPaginas={totalPaginas}
        totalRegistros={detalle?.count || 0}
        pageSize={pageSizeAplicado}
        allowedPageSizes={allowedPageSizes}
        onCambiarPagina={irAPagina}
        onCambiarPageSize={cambiarPageSize}
        cargando={cargando}
      />
    </div>
  )
}
