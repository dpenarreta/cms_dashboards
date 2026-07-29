import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const DrilldownContext = createContext(null)

const ESTADO_INICIAL = { abierto: false, titulo: '', origen: '', filtrosDrilldown: {} }

/**
 * Contrato único de drill-down (sección 12/13 del prompt de interactividad): transforma la
 * selección visual de un gráfico/KPI/celda en un conjunto de filtros y abre el panel de
 * detalle reutilizable, sin duplicar esta lógica en cada componente de gráfico.
 */
export function DrilldownProvider({ children }) {
  const [estado, setEstado] = useState(ESTADO_INICIAL)

  const abrirDetalle = useCallback(({ origen, titulo, filtros }) => {
    setEstado({ abierto: true, titulo: titulo || '', origen: origen || '', filtrosDrilldown: filtros || {} })
  }, [])

  const cerrarDetalle = useCallback(() => {
    setEstado((prev) => ({ ...prev, abierto: false }))
  }, [])

  const quitarFiltroDrilldown = useCallback((campo) => {
    setEstado((prev) => {
      const filtrosDrilldown = { ...prev.filtrosDrilldown }
      delete filtrosDrilldown[campo]
      return { ...prev, filtrosDrilldown }
    })
  }, [])

  const valor = useMemo(() => ({
    ...estado, abrirDetalle, cerrarDetalle, quitarFiltroDrilldown,
  }), [estado, abrirDetalle, cerrarDetalle, quitarFiltroDrilldown])

  return <DrilldownContext.Provider value={valor}>{children}</DrilldownContext.Provider>
}

export function useDrilldown() {
  const ctx = useContext(DrilldownContext)
  if (!ctx) {
    throw new Error('useDrilldown debe usarse dentro de un <DrilldownProvider>.')
  }
  return ctx
}
