import { Button, Offcanvas } from 'react-bootstrap'
import { useDrilldown } from '../../hooks/useDrilldown'
import ActiveFiltersSummary from './ActiveFiltersSummary'
import DetalleTable from '../table/DetalleTable'

/**
 * Panel de detalle reutilizable para el drill-down de cualquier gráfico/KPI/celda del
 * dashboard (sección 5-9 del prompt de interactividad). No existía un patrón de navegación a
 * una vista de detalle en el proyecto, así que se implementó como panel lateral (Offcanvas) en
 * vez de agregar una ruta nueva: al ser una superposición, "volver al dashboard" es
 * simplemente cerrar el panel, sin perder filtros ni scroll de la página de fondo.
 */
export default function PortfolioDetailPanel({ cargaId, fechaCorte, filtrosGlobales }) {
  const { abierto, titulo, filtrosDrilldown, cerrarDetalle, quitarFiltroDrilldown } = useDrilldown()

  const filtrosCombinados = { ...filtrosGlobales, ...filtrosDrilldown }

  return (
    <Offcanvas show={abierto} onHide={cerrarDetalle} placement="end" style={{ width: 'min(900px, 95vw)' }}>
      <Offcanvas.Header closeButton>
        <Offcanvas.Title>{titulo || 'Detalle de cartera'}</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <div className="mb-2 fw-semibold">Filtros aplicados</div>
        <ActiveFiltersSummary
          filtrosGlobales={filtrosGlobales}
          filtrosDrilldown={filtrosDrilldown}
          onQuitarFiltro={quitarFiltroDrilldown}
        />
        <div className="d-flex gap-2 mb-3">
          <Button size="sm" variant="outline-secondary" onClick={cerrarDetalle}>Volver al dashboard</Button>
        </div>

        {cargaId && (
          <DetalleTable cargaId={cargaId} filtros={filtrosCombinados} fechaCorte={fechaCorte} titulo="Registros seleccionados" />
        )}
      </Offcanvas.Body>
    </Offcanvas>
  )
}
