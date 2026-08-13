import { useEffect, useState } from 'react'
import { Alert, Button, OverlayTrigger, Spinner, Tooltip } from 'react-bootstrap'
import { Link, useParams } from 'react-router-dom'
import { DndContext, PointerSensor, useDroppable, useSensor, useSensors } from '@dnd-kit/core'
import { useGenericDashboardBuilder } from '../../hooks/useGenericDashboardBuilder'
import { useDashboardLayout } from '../../hooks/useDashboardLayout'
import { PERMISOS, usePermisos } from '../../hooks/usePermisos'
import { useAuth } from '../../context/AuthContext'
import FileUploadZone from '../../components/upload/FileUploadZone'
import RenameColumnsStep from '../../components/dashboard-generic/RenameColumnsStep'
import ValoresEnBlancoStep from '../../components/dashboard-generic/ValoresEnBlancoStep'
import TemplateMappingStep from '../../components/dashboard-generic/TemplateMappingStep'
import GenericChartRenderer from '../../components/dashboard-generic/GenericChartRenderer'
import GenericTitleBlock from '../../components/dashboard-generic/GenericTitleBlock'
import GenericSeparator from '../../components/dashboard-generic/GenericSeparator'
import TablaHistoricaAutomatica from '../../components/dashboard-generic/TablaHistoricaAutomatica'
import EditModeToolbar from '../../components/dashboard-editor/EditModeToolbar'
import EditableGrid from '../../components/dashboard-editor/EditableGrid'
import ComponentPropertiesPanel from '../../components/dashboard-editor/ComponentPropertiesPanel'
import AgregarComponentePersonalModal from '../../components/dashboard-editor/AgregarComponentePersonalModal'
import ComponentPaletteSidebar from '../../components/dashboard-editor/ComponentPaletteSidebar'
import ConfirmModal from '../../components/dashboard-editor/ConfirmModal'
import DashboardTabsBar from '../../components/dashboards/DashboardTabsBar'
import InterpretacionDashboardModal from '../../components/dashboards/InterpretacionDashboardModal'
import * as dashboardLayoutService from '../../services/dashboardLayoutService'
import * as historicoService from '../../services/historicoService'
import { construirOverride, datosDesdeComponente } from '../../utils/datosDesdeComponente'

// Tipos de la paleta sin datos (se crean de inmediato al soltar/elegir, sin pasar por
// `AgregarComponentePersonalModal`) — mapea el vocabulario de `ComponentPaletteSidebar` al
// `DashboardComponent.Tipo` real del backend (`title`/`text`).
const TIPO_BACKEND_PRESENTACIONAL = { titulo: 'title', separador: 'text' }

/** Único destino de suelta de la paleta de componentes (`ComponentPaletteSidebar`) — vive en un
 * `DndContext` separado del de `EditableGrid.jsx` (que gobierna el reordenamiento interno del
 * grid) para no interferir con esa lógica ya probada. Como es el ÚNICO droppable registrado en
 * ese `DndContext`, es estructuralmente imposible soltar un componente de la paleta en otro
 * lugar que no sea la Zona Personal — no depende de ninguna validación en tiempo de ejecución. */
function ZonaPersonalDropTarget() {
  const { isOver, setNodeRef } = useDroppable({ id: 'zona-personal-drop' })
  return (
    <div
      ref={setNodeRef}
      className="text-center text-secondary py-3 mb-3"
      style={{
        border: '2px dashed', borderRadius: 10,
        borderColor: isOver ? 'var(--bs-primary)' : undefined,
        background: isOver ? 'var(--bs-primary-bg-subtle)' : undefined,
      }}
    >
      Soltá aquí un componente para agregarlo a la Zona Personal
    </div>
  )
}

/**
 * Página de un dashboard por área. Todo dashboard nace con las 13 posiciones fijas de la
 * plantilla (`services/plantilla.py`, sembradas al crearlo) con datos ficticios — nunca vacío.
 * "Cargar otro archivo" abre el flujo `CARGA → RENOMBRAR → [VALORES_EN_BLANCO] → MAPEO`
 * (`useGenericDashboardBuilder`): analiza el archivo, deja renombrar cualquier columna y marcarla
 * como "histórica" (`RenameColumnsStep` — esa marca queda guardada por dashboard, se reconoce sola
 * en la próxima carga, y alimenta automáticamente Tabla 3, ver `columnasHistoricasConfiguradas`
 * más abajo), propone qué columna(s) usar en cada una de las 13 posiciones (`TemplateMappingStep`)
 * y, al confirmar, sobreescribe esas mismas posiciones con datos reales.
 * Cada posición sigue siendo un componente normal del layout (`useDashboardLayout`), así que
 * conserva el editor de grid (mover/redimensionar/ocultar/recolorear) ya existente.
 *
 * En modo edición, el panel lateral de componentes (`ComponentPaletteSidebar`) se abre solo al
 * entrar en modo edición y permite arrastrar (o hacer clic, como alternativa sin arrastre) un
 * tipo de componente hasta `ZonaPersonalDropTarget` — separador/título se crean de inmediato
 * (`dashboardLayoutService.agregarComponentePresentacional`); KPI/gráfico/tabla abren
 * `AgregarComponentePersonalModal` ya preseleccionado en ese tipo, porque necesitan elegir
 * columna(s) del archivo antes de poder calcular su contenido.
 */
export default function DashboardAreaPage() {
  const { dashboardId } = useParams()
  const [dashboardInfo, setDashboardInfo] = useState(null)
  const [mostrarConstructor, setMostrarConstructor] = useState(false)
  const [mostrarModalPersonal, setMostrarModalPersonal] = useState(false)
  const [tipoModalPersonal, setTipoModalPersonal] = useState(null)
  const [mostrarPaleta, setMostrarPaleta] = useState(false)
  const [mostrarInterpretacion, setMostrarInterpretacion] = useState(false)
  const [confirmandoAgregarTipo, setConfirmandoAgregarTipo] = useState(null)
  const builder = useGenericDashboardBuilder(dashboardId)
  const layout = useDashboardLayout(dashboardId)
  const permisos = usePermisos()
  const sensoresPaleta = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }))
  // `usePermisos()` es un stub que concede todo el editor visual siempre (ver `hooks/CLAUDE.md`)
  // — para gates reales de IA se usa `user.permissions` directo, igual que el resto de la app.
  const { user } = useAuth()
  const puedeInterpretar = Boolean(user?.permissions?.includes('dashboard.interpretar'))
  const puedeHallazgosIA = Boolean(user?.permissions?.includes('dashboard.hallazgos_ia'))

  // Las columnas que el usuario ya marcó como "históricas" para este dashboard (`ColumnaHistorica`,
  // configuración persistente — no lo que aparece en los datos ya guardados). Alimenta Tabla 3
  // en la vista normal del dashboard (más abajo) y, durante el asistente de carga, deja
  // pre-tildadas las mismas columnas en "Renombrar columnas" y avisa si alguna falta en el archivo
  // nuevo. Se pide siempre (no solo durante el asistente): Tabla 3 la necesita igual fuera de
  // él. `builder.fase` como dependencia hace que se refresque sola después de aplicar un mapeo
  // nuevo (esa acción vuelve la fase a CARGA).
  const [columnasHistoricasConfiguradas, setColumnasHistoricasConfiguradas] = useState([])
  useEffect(() => {
    let cancelado = false
    historicoService.listarCargasHistoricas(dashboardId)
      .then((resultado) => { if (!cancelado) setColumnasHistoricasConfiguradas(resultado.columnas_historicas_configuradas || []) })
      .catch(() => { if (!cancelado) setColumnasHistoricasConfiguradas([]) })
    return () => { cancelado = true }
  }, [dashboardId, builder.fase])

  // Pre-tilda, una vez por carga nueva (cuando aparece un `cargaId`), las columnas de ese archivo
  // que ya estaban marcadas como históricas antes — así el usuario no tiene que volver a elegirlas
  // a mano cada vez que sube un archivo de la misma fuente.
  useEffect(() => {
    if (builder.archivoInfo?.cargaId) {
      builder.inicializarColumnasHistoricas(columnasHistoricasConfiguradas)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- se dispara una vez por carga (cargaId), no en cada cambio de columnasHistoricasConfiguradas
  }, [builder.archivoInfo?.cargaId])

  // El título general y el área mostrados en el encabezado son siempre los del dashboard raíz de
  // la familia, no los de la pestaña activa (`listar_pestanas` ya resuelve la raíz sin importar
  // desde qué pestaña se llame) — el nombre de la pestaña en sí solo se ve en la barra de
  // pestañas, nunca reemplaza el título general.
  useEffect(() => {
    let cancelado = false
    dashboardLayoutService.obtenerPestanas(dashboardId).then((pestanas) => {
      const raiz = pestanas[0]
      if (!raiz) return
      dashboardLayoutService.obtenerDashboardsAutorizados().then((lista) => {
        const encontrado = lista.find((d) => d.dashboard_id === raiz.dashboard_id)
        if (!cancelado) setDashboardInfo(encontrado || { dashboard_id: raiz.dashboard_id, name: raiz.name, area: '' })
      })
      // Sin acceso a la familia de pestañas (control de acceso por dashboard): el título general
      // se queda en el fallback del `dashboardId` crudo — `layout.error`, más abajo, ya explica
      // por qué no se puede ver este dashboard.
    }).catch(() => {})
    return () => { cancelado = true }
  }, [dashboardId])

  // El panel de paleta se abre solo al entrar en modo edición — reacciona a la transición de
  // `layout.modoEdicion` en vez de acoplarse al clic puntual de "Editar dashboard", así también
  // queda correcto si el modo edición se activa por cualquier otro camino futuro.
  useEffect(() => {
    if (layout.modoEdicion) setMostrarPaleta(true)
  }, [layout.modoEdicion])

  // "Hallazgos clave" por componente generados por IA (`HallazgosClaveCard.jsx`) — un único
  // llamado batch para todo el dashboard, no uno por componente (evitaría N llamadas externas en
  // cada carga de página). Se pide una vez que el layout GUARDADO está disponible y se vuelve a
  // pedir solo cuando su versión cambia (nuevo archivo cargado, componente agregado/editado) — no
  // en cada movimiento sin guardar del borrador. Si falla o todavía no resolvió, cada
  // `HallazgosClaveCard` sigue mostrando su texto por reglas (fallback instantáneo) — por eso acá
  // no hay estado de error ni de carga, un `catch` silencioso alcanza. Sin `dashboard.hallazgos_ia`
  // ni siquiera se dispara la llamada (evita un 403 esperado en cada carga de página para
  // cualquier usuario sin ese permiso — la protección real de todos modos vive en el backend).
  const [hallazgosIA, setHallazgosIA] = useState({})
  useEffect(() => {
    if (!layout.layoutGuardado || !puedeHallazgosIA) return undefined
    let cancelado = false
    dashboardLayoutService.generarHallazgosIA(dashboardId)
      .then((resultado) => { if (!cancelado) setHallazgosIA(resultado.hallazgos || {}) })
      .catch(() => {})
    return () => { cancelado = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo debe repetirse cuando cambia la versión guardada, no en cada referencia nueva de layoutGuardado
  }, [dashboardId, layout.layoutGuardado?.version, puedeHallazgosIA])

  const cancelarConstructor = () => {
    builder.limpiar()
    setMostrarConstructor(false)
  }

  const confirmarMapeo = async () => {
    const resultado = await builder.confirmarMapeo()
    if (resultado.ok) {
      await layout.recargar()
      setMostrarConstructor(false)
    }
  }

  // Agregar un componente (desde la paleta, sea presentacional o vía el modal) persiste de
  // inmediato y refresca el layout con la última versión guardada en el servidor — no pasa por
  // "Guardar cambios". Si hay ediciones de diseño sin guardar (mover/ocultar/redimensionar), se
  // pide confirmación antes de perderlas en silencio (`manejarElegirTipo`); esta función solo
  // ejecuta la acción ya confirmada.
  const ejecutarAgregarTipo = async (tipo) => {
    if (tipo in TIPO_BACKEND_PRESENTACIONAL) {
      await dashboardLayoutService.agregarComponentePresentacional(dashboardId, {
        tipo: TIPO_BACKEND_PRESENTACIONAL[tipo], zona: 'personal',
      })
      await layout.recargar()
      return
    }
    setTipoModalPersonal(tipo)
    setMostrarModalPersonal(true)
  }

  const manejarElegirTipo = (tipo) => {
    if (layout.hayCambiosSinGuardar()) {
      setConfirmandoAgregarTipo(tipo)
      return
    }
    ejecutarAgregarTipo(tipo)
  }

  const manejarSoltarPaleta = (event) => {
    const { active, over } = event
    if (over?.id !== 'zona-personal-drop') return
    if (typeof active.id !== 'string' || !active.id.startsWith('paleta-')) return
    manejarElegirTipo(active.id.replace('paleta-', ''))
  }

  const cargandoInicial = layout.layoutGuardado === null
  const mostrandoConstructor = !cargandoInicial && mostrarConstructor
  // El panel de paleta y `ComponentPropertiesPanel` (ambos `Offcanvas placement="end"`) quedan
  // mutuamente excluyentes sin estado extra: al seleccionar un componente existente para
  // configurarlo, la paleta se oculta sola; al cerrar el panel de propiedades, reaparece si
  // seguía activa.
  const mostrarPaletaEfectivo = mostrarPaleta && !layout.seleccionado

  const registro = Object.fromEntries(layout.borrador.map((c) => [
    c.component_id,
    {
      render: (componente) => {
        if (componente.type === 'title') return <GenericTitleBlock content={componente.content} />
        if (componente.type === 'text') return <GenericSeparator content={componente.content} />
        if (componente.type !== 'kpi' && componente.type !== 'chart') return null
        const override = construirOverride(componente)
        const { datos, datosMultiserie } = datosDesdeComponente(componente)
        const esTablaHistorica = componente.component_id === 'tabla-3'
        const contenidoNormal = (
          <GenericChartRenderer
            tipoVisualizacion={componente.type === 'kpi' ? 'kpi' : (componente.chart_type || 'barras_horizontales')}
            datos={datos}
            datosMultiserie={datosMultiserie}
            titulo={componente.content?.titulo}
            override={override}
            config={componente.config}
            esHistorica={esTablaHistorica}
            hallazgoIA={hallazgosIA[componente.component_id]}
          />
        )
        // Tabla 3 es la única posición que, en vez de mostrar el detalle del archivo actual,
        // compara en vivo las cargas históricas HABILITADAS del dashboard (ver
        // `TablaHistoricaAutomatica.jsx`) — cae a `contenidoNormal` si todavía no hay historial
        // habilitado o esta posición no tiene columnas mapeadas.
        if (esTablaHistorica) {
          return (
            <TablaHistoricaAutomatica
              dashboardId={dashboardId}
              columnasValor={columnasHistoricasConfiguradas.map((nombre) => ({ columna: nombre, tipo_agregacion: 'suma' }))}
              override={override}
              contenidoNormal={contenidoNormal}
            />
          )
        }
        return contenidoNormal
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
          {puedeInterpretar && (
            <Button variant="outline-secondary" size="sm" onClick={() => setMostrarInterpretacion(true)}>
              Interpretación completa
            </Button>
          )}
          <OverlayTrigger placement="top" overlay={<Tooltip>Disponible en una fase futura.</Tooltip>}>
            <span>
              <Button variant="outline-secondary" size="sm" disabled>Conectar vista de base de datos</Button>
            </span>
          </OverlayTrigger>
          <Button as={Link} to={`/app/dashboards/${dashboardId}/historico`} variant="outline-secondary" size="sm">
            Ver histórico
          </Button>
          {!mostrarConstructor && (
            <Button variant="outline-secondary" size="sm" onClick={() => setMostrarConstructor(true)}>Cargar otro archivo</Button>
          )}
        </div>
      </div>

      {/* Un `layout.error` durante la carga inicial (p. ej. 403 del control de acceso por
          dashboard: el usuario no es dueño/superusuario ni tiene un rol asignado) corta acá — ni
          la barra de pestañas ni el resto de la página tienen nada válido que mostrar. */}
      {cargandoInicial && layout.error && <Alert variant="danger">{layout.error}</Alert>}

      {!(cargandoInicial && layout.error) && (
        <DashboardTabsBar dashboardId={dashboardId} modoEdicion={layout.modoEdicion} />
      )}

      {cargandoInicial && !layout.error && <div className="text-center mb-3" role="status"><Spinner animation="border" /></div>}

      {!cargandoInicial && mostrandoConstructor && (
        <>
          {builder.fase === builder.FASE.CARGA && (
            <>
              <FileUploadZone onValidar={(archivo) => builder.subirYValidar(archivo)} cargando={builder.cargando} error={builder.error} />
              <div className="mt-2">
                <Button variant="outline-secondary" size="sm" onClick={cancelarConstructor}>Cancelar</Button>
              </div>
            </>
          )}

          {builder.fase === builder.FASE.RENOMBRAR && (
            <RenameColumnsStep
              archivoInfo={builder.archivoInfo}
              columnas={builder.columnasOriginales}
              aliases={builder.aliases}
              onActualizarAlias={builder.actualizarAlias}
              onContinuar={builder.confirmarRenombrado}
              onCancelar={builder.cancelarRenombrado}
              cargando={builder.cargando}
              error={builder.error}
              columnasHistoricas={builder.columnasHistoricas}
              onCambiarColumnaHistorica={builder.actualizarColumnaHistorica}
              columnasHistoricasConfiguradas={columnasHistoricasConfiguradas}
            />
          )}

          {builder.fase === builder.FASE.VALORES_EN_BLANCO && (
            <ValoresEnBlancoStep
              archivoInfo={builder.archivoInfo}
              columnasConBlancos={builder.columnasConBlancos}
              valoresBlancos={builder.valoresBlancos}
              columnas={builder.columnas}
              columnasHistoricas={builder.columnasHistoricasFinales}
              onActualizarValorBlanco={builder.actualizarValorBlanco}
              onContinuar={builder.confirmarValoresBlancos}
              onCancelar={builder.cancelarValoresBlancos}
              cargando={builder.cargando}
              error={builder.error}
            />
          )}

          {builder.fase === builder.FASE.MAPEO && (
            <TemplateMappingStep
              archivoInfo={builder.archivoInfo}
              columnas={builder.columnas}
              mapeo={builder.mapeo}
              datos={builder.datos}
              aliases={builder.aliases}
              valoresBlancos={builder.valoresBlancos}
              onActualizarSlot={builder.actualizarMapeoSlot}
              onConfirmar={confirmarMapeo}
              onCancelar={builder.cancelarMapeo}
              cargando={builder.cargando}
              cargandoPreview={builder.cargandoPreview}
              error={builder.error}
              columnasConBlancos={builder.columnasConBlancos}
              columnasHistoricas={builder.columnasHistoricasFinales}
            />
          )}
        </>
      )}

      {!cargandoInicial && !mostrandoConstructor && (
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

          <DndContext sensors={sensoresPaleta} onDragEnd={manejarSoltarPaleta}>
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

            {layout.modoEdicion && mostrarPaletaEfectivo && <ZonaPersonalDropTarget />}

            <ComponentPaletteSidebar
              show={layout.modoEdicion && mostrarPaletaEfectivo}
              onHide={() => setMostrarPaleta(false)}
              onElegirTipo={manejarElegirTipo}
            />
          </DndContext>

          {layout.modoEdicion && !layout.vistaPrevia && (
            <ComponentPropertiesPanel
              componente={layout.seleccionado ? layout.borrador.find((c) => c.component_id === layout.seleccionado) : null}
              dashboardId={dashboardId}
              onCerrar={() => layout.setSeleccionado(null)}
              onActualizarContenido={layout.actualizarContenido}
              onActualizarEstilos={layout.actualizarEstilos}
              onCambiarAncho={(id, w) => layout.actualizarComponente(id, { width: w })}
              onCambiarAlto={(id, h) => layout.actualizarComponente(id, { height: h })}
              onActualizarConfig={(id, config) => layout.actualizarComponente(id, { config })}
              onActualizarComponente={layout.actualizarComponente}
            />
          )}

          <AgregarComponentePersonalModal
            show={mostrarModalPersonal}
            onHide={() => setMostrarModalPersonal(false)}
            dashboardId={dashboardId}
            componentesPersonales={layout.borrador.filter((c) => c.config?.zona === 'personal')}
            tipoInicial={tipoModalPersonal}
            onAgregado={async () => {
              await layout.recargar()
              setMostrarModalPersonal(false)
            }}
          />

          <ConfirmModal
            show={Boolean(confirmandoAgregarTipo)}
            title="Agregar a la Zona Personal"
            confirmLabel="Continuar"
            confirmVariant="primary"
            onConfirm={() => {
              const tipo = confirmandoAgregarTipo
              setConfirmandoAgregarTipo(null)
              ejecutarAgregarTipo(tipo)
            }}
            onCancel={() => setConfirmandoAgregarTipo(null)}
          >
            <Alert variant="warning" className="mb-0">
              Agregar un componente a la Zona Personal se guarda de inmediato y actualiza el
              dashboard con la última versión guardada en el servidor — tus cambios de diseño sin
              guardar se perderán. ¿Continuar?
            </Alert>
          </ConfirmModal>
        </>
      )}

      <InterpretacionDashboardModal
        show={mostrarInterpretacion}
        onHide={() => setMostrarInterpretacion(false)}
        dashboardId={dashboardId}
      />
    </div>
  )
}
