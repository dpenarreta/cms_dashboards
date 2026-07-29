import { Alert, Button, Spinner } from 'react-bootstrap'
import { useCarteraDashboard } from '../hooks/useCarteraDashboard'
import { useDetalleCartera } from '../hooks/useDetalleCartera'
import { useDashboardLayout } from '../hooks/useDashboardLayout'
import { PERMISOS, usePermisos } from '../hooks/usePermisos'
import { DrilldownProvider } from '../hooks/useDrilldown'
import FileUploadZone from '../components/upload/FileUploadZone'
import ColumnMappingTable from '../components/mapping/ColumnMappingTable'
import { KpiCarteraNoVencida, KpiCarteraTotal, KpiCarteraVencida, KpiClientesUnicos, KpiMayor120, KpiMayor360 } from '../components/kpi/KpiRow'
import TopClientesChart from '../components/charts/TopClientesChart'
import CarteraVencidaPorCiudadChart from '../components/charts/CarteraVencidaPorCiudadChart'
import RecuperadoresChart from '../components/charts/RecuperadoresChart'
import CausalesChart from '../components/charts/CausalesChart'
import RecuperadorCausalChart from '../components/charts/RecuperadorCausalChart'
import RecuperadorCausalMatrix from '../components/charts/RecuperadorCausalMatrix'
import FiltersPanel from '../components/filters/FiltersPanel'
import DetalleTable from '../components/table/DetalleTable'
import PortfolioDetailPanel from '../components/drilldown/PortfolioDetailPanel'
import EditModeToolbar from '../components/dashboard-editor/EditModeToolbar'
import EditableGrid from '../components/dashboard-editor/EditableGrid'
import ComponentPropertiesPanel from '../components/dashboard-editor/ComponentPropertiesPanel'
import { formatDate } from '../utils/format'

const DASHBOARD_ID = 'cartera'

function construirOverride(componente) {
  return {
    titulo: componente?.content?.titulo || undefined,
    descripcion: componente?.content?.descripcion || undefined,
    colores: componente?.styles || {},
  }
}

function DashboardContenido({ dash }) {
  const cargaId = dash.archivoInfo?.cargaId
  const resumenDetalle = useDetalleCartera({
    cargaId, filtros: dash.filtrosAplicados, fechaCorte: dash.fechaCorte, pageSize: 1,
  })
  const layout = useDashboardLayout(DASHBOARD_ID)
  const permisos = usePermisos()

  const porId = Object.fromEntries(layout.borrador.map((c) => [c.component_id, c]))

  const registro = {
    'titulo-cartera': {
      render: () => {
        const plantilla = porId['titulo-cartera']?.content?.titulo || 'Cartera con corte al {fecha_corte}'
        return (
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <h5 className="mb-0">{plantilla.replace('{fecha_corte}', formatDate(dash.fechaCorte))}</h5>
            <div className="d-flex align-items-center gap-2">
              <label className="mb-0" style={{ fontSize: '0.85rem' }} htmlFor="input-fecha-corte">Fecha de corte</label>
              <input
                id="input-fecha-corte"
                type="date"
                className="form-control form-control-sm"
                style={{ width: 'auto' }}
                value={dash.fechaCorte}
                onChange={(e) => dash.cambiarFechaCorte(e.target.value)}
              />
            </div>
          </div>
        )
      },
    },
    'mensaje-resumen-validacion': {
      render: () => (dash.resumenValidacion ? (
        <Alert variant="info" className="mb-0">
          {dash.resumenValidacion.filas_leidas} filas leídas · {dash.resumenValidacion.filas_validas} válidas ·{' '}
          {dash.resumenValidacion.filas_con_advertencia} con advertencia · {dash.resumenValidacion.filas_descartadas} descartadas.
          {dash.resumenValidacion.advertencias_generales?.length > 0 && (
            <ul className="mb-0 mt-2">
              {dash.resumenValidacion.advertencias_generales.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          )}
        </Alert>
      ) : <div className="chart-panel__subtitle mb-0">Sin advertencias de validación.</div>),
    },
    'alerta-sin-fecha': {
      render: () => (dash.kpis?.sin_fecha_vencimiento?.valor > 0 ? (
        <Alert variant="warning" className="mb-0">
          {dash.kpis.sin_fecha_vencimiento.documentos} documento(s) sin fecha de vencimiento por un saldo de{' '}
          {dash.kpis.sin_fecha_vencimiento.valor} ({dash.kpis.sin_fecha_vencimiento.porcentaje}% de la cartera total).
        </Alert>
      ) : <div className="chart-panel__subtitle mb-0">Sin alertas de fecha faltante.</div>),
    },
    'kpi-clientes-unicos': { render: () => <KpiClientesUnicos kpis={dash.kpis} override={construirOverride(porId['kpi-clientes-unicos'])} /> },
    'kpi-cartera-total': { render: () => <KpiCarteraTotal kpis={dash.kpis} override={construirOverride(porId['kpi-cartera-total'])} /> },
    'kpi-cartera-vencida': { render: () => <KpiCarteraVencida kpis={dash.kpis} override={construirOverride(porId['kpi-cartera-vencida'])} /> },
    'kpi-cartera-no-vencida': { render: () => <KpiCarteraNoVencida kpis={dash.kpis} override={construirOverride(porId['kpi-cartera-no-vencida'])} /> },
    'kpi-mayor-120': { render: () => <KpiMayor120 kpis={dash.kpis} override={construirOverride(porId['kpi-mayor-120'])} /> },
    'kpi-mayor-360': { render: () => <KpiMayor360 kpis={dash.kpis} override={construirOverride(porId['kpi-mayor-360'])} /> },
    'panel-filtros': {
      render: () => (
        <FiltersPanel
          filtros={dash.filtrosBorrador}
          onCambiarFiltro={dash.actualizarFiltroBorrador}
          onAplicar={dash.aplicarFiltros}
          onLimpiar={dash.limpiarFiltros}
          recuperadores={dash.recuperadores}
          causales={dash.causales}
          resumenFiltrado={resumenDetalle.detalle}
          configuracionFiltros={porId['panel-filtros']?.config?.filtros}
          override={construirOverride(porId['panel-filtros'])}
        />
      ),
    },
    'chart-top-clientes': {
      render: () => <TopClientesChart data={dash.topClientes} override={construirOverride(porId['chart-top-clientes'])} />,
    },
    'chart-cartera-vencida-ciudad': {
      render: () => <CarteraVencidaPorCiudadChart data={dash.paretoCiudades} override={construirOverride(porId['chart-cartera-vencida-ciudad'])} />,
    },
    'chart-recuperadores': {
      render: () => <RecuperadoresChart data={dash.recuperadores} override={construirOverride(porId['chart-recuperadores'])} />,
    },
    'chart-causales': {
      render: () => <CausalesChart data={dash.causales} override={construirOverride(porId['chart-causales'])} />,
    },
    'chart-recuperador-causal': {
      render: () => (
        <RecuperadorCausalChart
          data={dash.recuperadorCausalChart}
          metrica={dash.metricaRecuperadorCausal}
          onCambiarMetrica={dash.cambiarMetricaRecuperadorCausal}
          override={construirOverride(porId['chart-recuperador-causal'])}
        />
      ),
    },
    'tabla-matriz-recuperador-causal': {
      render: () => (
        <RecuperadorCausalMatrix
          matriz={dash.recuperadorCausalMatriz}
          metrica={dash.metricaRecuperadorCausal}
          override={construirOverride(porId['tabla-matriz-recuperador-causal'])}
        />
      ),
    },
    'tabla-detalle': {
      render: () => (
        <DetalleTable
          cargaId={cargaId}
          filtros={dash.filtrosAplicados}
          fechaCorte={dash.fechaCorte}
          resumenValidacion={dash.resumenValidacion}
          override={construirOverride(porId['tabla-detalle'])}
        />
      ),
    },
  }

  return (
    <>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <div className="chart-panel__subtitle mb-0">Diseño del dashboard</div>
        <EditModeToolbar
          modoEdicion={layout.modoEdicion}
          vistaPrevia={layout.vistaPrevia}
          cargando={layout.cargando}
          hayCambiosSinGuardar={layout.hayCambiosSinGuardar}
          onActivarEdicion={layout.activarEdicion}
          onGuardar={layout.guardar}
          onCancelar={layout.cancelar}
          onAlternarVistaPrevia={layout.alternarVistaPrevia}
          onRestablecer={layout.restablecer}
        />
      </div>

      {layout.error && <Alert variant="danger">{layout.error}</Alert>}
      {layout.conflicto && (
        <Alert variant="warning" className="d-flex justify-content-between align-items-center">
          <span>Existe una versión más reciente de este dashboard guardada por otra persona.</span>
          <Button size="sm" variant="warning" onClick={layout.recargarPorConflicto}>Recargar configuración</Button>
        </Alert>
      )}

      {dash.error && <Alert variant="danger">{dash.error}</Alert>}

      {!layout.layoutGuardado ? (
        <div className="text-center mb-3"><Spinner animation="border" /></div>
      ) : (
        <EditableGrid
          componentes={layout.borrador}
          registro={registro}
          modoEdicion={layout.modoEdicion}
          vistaPrevia={layout.vistaPrevia}
          seleccionado={layout.seleccionado}
          onSeleccionar={layout.setSeleccionado}
          onMover={layout.moverComponente}
          onOcultar={(id) => layout.actualizarComponente(id, { is_visible: false })}
          onMostrar={(id) => layout.actualizarComponente(id, { is_visible: true })}
          onReordenar={layout.reordenarPorIds}
          permiteEstilo={permisos.tiene(PERMISOS.DASHBOARD_COMPONENT_STYLE)}
        />
      )}

      {dash.cargando && <div className="text-center mb-3"><Spinner animation="border" /></div>}

      {layout.modoEdicion && !layout.vistaPrevia && (
        <ComponentPropertiesPanel
          componente={layout.seleccionado ? porId[layout.seleccionado] : null}
          onCerrar={() => layout.setSeleccionado(null)}
          onActualizarContenido={layout.actualizarContenido}
          onActualizarEstilos={layout.actualizarEstilos}
          onCambiarAncho={(id, w) => layout.actualizarComponente(id, { width: w })}
          onCambiarAlto={(id, h) => layout.actualizarComponente(id, { height: h })}
          onActualizarConfig={(id, config) => layout.actualizarComponente(id, { config })}
        />
      )}

      <PortfolioDetailPanel cargaId={cargaId} fechaCorte={dash.fechaCorte} filtrosGlobales={dash.filtrosAplicados} />
    </>
  )
}

export default function CarteraDashboardPage() {
  const dash = useCarteraDashboard()

  return (
    <div className="cartera-app">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3 className="mb-0">Dashboard de Cartera</h3>
        {dash.fase !== dash.FASE.CARGA && (
          <Button variant="outline-secondary" size="sm" onClick={dash.limpiar}>Cargar otro archivo</Button>
        )}
      </div>

      {dash.fase === dash.FASE.CARGA && (
        <FileUploadZone onValidar={(archivo) => dash.subirYValidar(archivo)} cargando={dash.cargando} error={dash.error} />
      )}

      {dash.fase === dash.FASE.MAPEO && (
        <ColumnMappingTable
          archivoInfo={dash.archivoInfo}
          mapeoSugerido={dash.mapeoSugerido}
          mapeoConfirmado={dash.mapeoConfirmado}
          onActualizarMapeo={dash.actualizarMapeo}
          previewFilas={dash.previewFilas}
          onProcesar={dash.procesar}
          onLimpiar={dash.limpiar}
          onCambiarHoja={dash.cambiarHoja}
          cargando={dash.cargando}
          error={dash.error}
          fechaCorte={dash.fechaCorte}
          onCambiarFechaCorte={dash.cambiarFechaCorte}
        />
      )}

      {dash.fase === dash.FASE.DASHBOARD && (
        <DrilldownProvider>
          <DashboardContenido dash={dash} />
        </DrilldownProvider>
      )}
    </div>
  )
}
