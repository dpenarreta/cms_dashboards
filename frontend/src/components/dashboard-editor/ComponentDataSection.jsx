import { useEffect, useState } from 'react'
import { Alert, Spinner } from 'react-bootstrap'
import * as carteraService from '../../services/carteraService'
import { FiltroSlot, camposParaSlot } from '../dashboard-generic/SlotFields'
import { PLANTILLA_SLOTS } from '../../utils/plantillaSlots'

/**
 * Sección "Datos" de "Configurar componente": reconfigura qué columna(s)/tipo de cálculo/tipo de
 * gráfico/filtro alimentan una de las 13 posiciones fijas de la plantilla, ya aplicada — mismos
 * selectores que el mapeo inicial tras cargar un archivo (`TemplateMappingStep`, vía
 * `SlotFields`), pero sobre el archivo permanente del dashboard
 * (`plantilla/archivo-actual`, guardado al aplicar — ver `services/plantilla.py`) en vez del de
 * una sesión de carga en curso. Cada cambio recalcula la posición en el momento
 * (`previsualizarMapeoPlantilla`) y actualiza el borrador del layout (`onActualizarComponente`);
 * recién queda persistido cuando el usuario guarda el diseño desde la barra de edición, igual que
 * el resto de cambios de este panel (título, colores, tamaño...).
 */
export default function ComponentDataSection({ componente, dashboardId, onActualizarComponente }) {
  const [archivoActual, setArchivoActual] = useState(null)
  const [cargandoArchivo, setCargandoArchivo] = useState(true)
  const [errorArchivo, setErrorArchivo] = useState('')
  const [cargandoPreview, setCargandoPreview] = useState(false)

  useEffect(() => {
    let cancelado = false
    setCargandoArchivo(true)
    setErrorArchivo('')
    carteraService.obtenerArchivoActualDashboard(dashboardId)
      .then((resultado) => { if (!cancelado) setArchivoActual(resultado) })
      .catch(() => { if (!cancelado) setErrorArchivo('No se pudo cargar la información del archivo de este dashboard.') })
      .finally(() => { if (!cancelado) setCargandoArchivo(false) })
    return () => { cancelado = true }
  }, [dashboardId])

  const slot = PLANTILLA_SLOTS.find((s) => s.id === componente.component_id)

  if (!slot) {
    return <div className="chart-panel__subtitle mb-0">Esta posición no tiene datos configurables desde acá.</div>
  }

  if (cargandoArchivo) {
    return <div className="text-center py-3"><Spinner animation="border" size="sm" /></div>
  }

  if (errorArchivo) {
    return <Alert variant="danger" className="py-2" style={{ fontSize: '0.85rem' }}>{errorArchivo}</Alert>
  }

  if (!archivoActual?.disponible) {
    return (
      <div className="chart-panel__subtitle mb-0">
        Este dashboard todavía no tiene un archivo real cargado. Usa "Cargar otro archivo" para
        poder configurar los datos de este componente.
      </div>
    )
  }

  const propuesta = componente.mapeo || {}
  const columnas = archivoActual.columnas

  const recalcular = async (nuevoMapeo) => {
    setCargandoPreview(true)
    try {
      const resultado = await carteraService.previsualizarMapeoPlantilla(archivoActual.carga_id, { [componente.component_id]: nuevoMapeo })
      onActualizarComponente(componente.component_id, { mapeo: nuevoMapeo, content: resultado.datos[componente.component_id] })
    } catch {
      // La vista previa es de mejor esfuerzo: el mapeo elegido igual queda guardado en el
      // borrador (se puede reintentar el cálculo cambiando cualquier otro campo).
      onActualizarComponente(componente.component_id, { mapeo: nuevoMapeo })
    } finally {
      setCargandoPreview(false)
    }
  }

  const cambiar = (campo) => (valor) => {
    const nuevoMapeo = { ...propuesta, [campo]: valor, disponible: true }
    if (campo === 'chart_type') {
      // El tipo de gráfico no cambia los datos calculados, solo cómo se dibujan — no hace falta
      // recalcular contra el archivo.
      onActualizarComponente(componente.component_id, { mapeo: nuevoMapeo, chart_type: valor })
      return
    }
    recalcular(nuevoMapeo)
  }

  const cambiarLista = (campo) => (nuevaLista) => recalcular({ ...propuesta, [campo]: nuevaLista, disponible: true })

  return (
    <div>
      <div className="chart-panel__subtitle d-flex align-items-center gap-2 flex-wrap mb-2">
        <span>Archivo: {archivoActual.nombre_archivo} · {archivoActual.total_filas} fila(s)</span>
        {cargandoPreview && (
          <span className="d-inline-flex align-items-center gap-1">
            <Spinner animation="border" size="sm" role="status" />
            Actualizando…
          </span>
        )}
      </div>
      {camposParaSlot({ slot, propuesta, columnas, cambiar, cambiarLista })}
      <FiltroSlot
        contexto={slot.titulo}
        cargaId={archivoActual.carga_id}
        columnas={columnas}
        columnaFiltro={propuesta.columna_filtro}
        valorFiltro={propuesta.valor_filtro}
        onCambiarColumna={(valor) => recalcular({ ...propuesta, columna_filtro: valor, valor_filtro: null, disponible: true })}
        onCambiarValor={(valor) => recalcular({ ...propuesta, valor_filtro: valor, disponible: true })}
      />
    </div>
  )
}
