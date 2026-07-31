import { useEffect, useState } from 'react'
import { Alert, Button, OverlayTrigger, Spinner, Tooltip } from 'react-bootstrap'
import { useParams } from 'react-router-dom'
import { useGenericDashboardBuilder } from '../../hooks/useGenericDashboardBuilder'
import { useDashboardLayout } from '../../hooks/useDashboardLayout'
import { PERMISOS, usePermisos } from '../../hooks/usePermisos'
import FileUploadZone from '../../components/upload/FileUploadZone'
import ColumnAliasStep from '../../components/dashboard-generic/ColumnAliasStep'
import ChartRecommendations from '../../components/dashboard-generic/ChartRecommendations'
import GenericChartRenderer from '../../components/dashboard-generic/GenericChartRenderer'
import EditModeToolbar from '../../components/dashboard-editor/EditModeToolbar'
import EditableGrid from '../../components/dashboard-editor/EditableGrid'
import ComponentPropertiesPanel from '../../components/dashboard-editor/ComponentPropertiesPanel'
import DashboardPlaceholderTemplate from '../../components/dashboard-generic/DashboardPlaceholderTemplate'
import * as dashboardLayoutService from '../../services/dashboardLayoutService'

function construirOverride(componente) {
  return {
    titulo: componente?.content?.titulo || undefined,
    descripcion: componente?.content?.descripcion || undefined,
    colores: componente?.styles || {},
  }
}

const TIPOS_MULTISERIE = new Set(['barras_agrupadas', 'barras_apiladas', 'area_apilada'])

/** Reconstruye la forma `{tipo, ...}` que esperan los renderers genéricos a partir de lo que
 * quedó guardado en `component.content` (ver `dashboard_layout.py::agregar_componente_generado`
 * para el lado que lo escribe). */
function datosDesdeComponente(componente) {
  if (componente.type === 'kpi') {
    return { datos: { tipo: 'kpi', valor: componente.content?.valor } }
  }
  if (componente.chart_type === 'dispersion') {
    return { datos: { tipo: 'dispersion', puntos: componente.content?.puntos } }
  }
  if (TIPOS_MULTISERIE.has(componente.chart_type)) {
    return { datosMultiserie: { tipo: 'multiserie', categorias: componente.content?.categorias, series: componente.content?.series } }
  }
  return { datos: { tipo: 'chart', categorias: componente.content?.categorias, valores: componente.content?.valores } }
}

/**
 * Página de un dashboard por área. El pipeline de KPIs fijos de cartera (mapeo obligatorio de
 * columnas de negocio) se reemplazó por un flujo genérico: cargar archivo → reconocer columnas y
 * confirmar alias → recomendar gráficas → agregar las que sirvan, una por una
 * (`useGenericDashboardBuilder`). Cada gráfica agregada se guarda como un componente normal del
 * layout (`useDashboardLayout`), así que conserva el editor de grid (mover/redimensionar/ocultar
 * /recolorear) ya existente.
 */
export default function DashboardAreaPage() {
  const { dashboardId } = useParams()
  const [dashboardInfo, setDashboardInfo] = useState(null)
  const [mostrarConstructor, setMostrarConstructor] = useState(false)
  const builder = useGenericDashboardBuilder(dashboardId)
  const layout = useDashboardLayout(dashboardId)
  const permisos = usePermisos()

  useEffect(() => {
    let cancelado = false
    dashboardLayoutService.obtenerDashboardsAutorizados()
      .then((lista) => { if (!cancelado) setDashboardInfo(lista.find((d) => d.dashboard_id === dashboardId) || null) })
    return () => { cancelado = true }
  }, [dashboardId])

  const cancelarConstructor = () => {
    builder.limpiar()
    setMostrarConstructor(false)
  }

  const finalizarConstructor = async () => {
    await layout.recargar()
    setMostrarConstructor(false)
  }

  const cargandoInicial = layout.layoutGuardado === null
  const hayComponentes = layout.borrador.length > 0
  const mostrandoConstructor = !cargandoInicial && (!hayComponentes || mostrarConstructor)

  const registro = Object.fromEntries(layout.borrador.map((c) => [
    c.component_id,
    {
      render: (componente) => {
        if (componente.type !== 'kpi' && componente.type !== 'chart') return null
        const override = construirOverride(componente)
        const { datos, datosMultiserie } = datosDesdeComponente(componente)
        return (
          <GenericChartRenderer
            tipoVisualizacion={componente.type === 'kpi' ? 'kpi' : (componente.chart_type || 'barras_horizontales')}
            datos={datos}
            datosMultiserie={datosMultiserie}
            titulo={componente.content?.titulo}
            override={override}
            config={componente.config}
          />
        )
      },
    },
  ]))

  return (
    <div className="cartera-app">
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
        <div>
          <h3 className="mb-1">{dashboardInfo?.name || dashboardId}</h3>
          {dashboardInfo?.area && <p className="chart-panel__subtitle mb-0">Área: {dashboardInfo.area}</p>}
        </div>
        <div className="d-flex gap-2">
          <OverlayTrigger placement="top" overlay={<Tooltip>Disponible en una fase futura.</Tooltip>}>
            <span>
              <Button variant="outline-secondary" size="sm" disabled>Conectar vista de base de datos</Button>
            </span>
          </OverlayTrigger>
          {hayComponentes && !mostrarConstructor && (
            <Button variant="outline-secondary" size="sm" onClick={() => setMostrarConstructor(true)}>Cargar otro archivo</Button>
          )}
        </div>
      </div>

      {cargandoInicial && <div className="text-center mb-3" role="status"><Spinner animation="border" /></div>}

      {!cargandoInicial && mostrandoConstructor && (
        <>
          {builder.fase === builder.FASE.CARGA && (
            <>
              <FileUploadZone onValidar={(archivo) => builder.subirYValidar(archivo)} cargando={builder.cargando} error={builder.error} />
              {hayComponentes && (
                <div className="mt-2">
                  <Button variant="outline-secondary" size="sm" onClick={cancelarConstructor}>Cancelar</Button>
                </div>
              )}
              {!hayComponentes && (
                <div className="mt-4">
                  <p className="chart-panel__subtitle">
                    Así se vería un dashboard terminado — carga un archivo arriba para armar el tuyo con tus propios datos.
                  </p>
                  <DashboardPlaceholderTemplate />
                </div>
              )}
            </>
          )}

          {builder.fase === builder.FASE.ALIAS && (
            <ColumnAliasStep
              archivoInfo={builder.archivoInfo}
              columnas={builder.columnas}
              aliases={builder.aliases}
              utilizables={builder.utilizables}
              onActualizarAlias={builder.actualizarAlias}
              onActualizarUtilizable={builder.actualizarUtilizable}
              onContinuar={builder.confirmarAliases}
              cargando={builder.cargando}
              error={builder.error}
            />
          )}

          {builder.fase === builder.FASE.RECOMENDACIONES && (
            <ChartRecommendations
              recomendaciones={builder.recomendaciones}
              aliases={builder.aliases}
              agregadas={builder.agregadas}
              onAgregar={builder.agregarGrafica}
              onVolver={builder.volverAAlias}
              onFinalizar={finalizarConstructor}
              cargando={builder.cargando}
              error={builder.error}
            />
          )}
        </>
      )}

      {!cargandoInicial && !mostrandoConstructor && hayComponentes && (
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
            onEliminar={layout.eliminarComponente}
            onReordenar={layout.reordenarPorIds}
            permiteEstilo={permisos.tiene(PERMISOS.DASHBOARD_COMPONENT_STYLE)}
            permiteEliminar={permisos.tiene(PERMISOS.DASHBOARD_COMPONENT_DELETE)}
          />

          {layout.modoEdicion && !layout.vistaPrevia && (
            <ComponentPropertiesPanel
              componente={layout.seleccionado ? layout.borrador.find((c) => c.component_id === layout.seleccionado) : null}
              onCerrar={() => layout.setSeleccionado(null)}
              onActualizarContenido={layout.actualizarContenido}
              onActualizarEstilos={layout.actualizarEstilos}
              onCambiarAncho={(id, w) => layout.actualizarComponente(id, { width: w })}
              onCambiarAlto={(id, h) => layout.actualizarComponente(id, { height: h })}
              onActualizarConfig={(id, config) => layout.actualizarComponente(id, { config })}
            />
          )}
        </>
      )}
    </div>
  )
}
