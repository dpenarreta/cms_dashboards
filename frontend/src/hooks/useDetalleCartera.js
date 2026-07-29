import { useCallback, useEffect, useState } from 'react'
import * as carteraService from '../services/carteraService'

const PAGE_SIZE_DEFECTO = 50

function limpiarParams(params) {
  const limpio = { ...params }
  Object.keys(limpio).forEach((k) => {
    if (limpio[k] === '' || limpio[k] === null || limpio[k] === undefined) delete limpio[k]
  })
  return limpio
}

/**
 * Hook único para consultar el detalle paginado de cartera (sección 11 y drill-down).
 * Lo usan tanto la tabla principal del dashboard como el panel de detalle del drill-down,
 * para no duplicar la lógica de paginación/orden/búsqueda en cada componente.
 */
export function useDetalleCartera({ cargaId, filtros, fechaCorte, pageSize = PAGE_SIZE_DEFECTO }) {
  const [pagina, setPagina] = useState(1)
  const [orden, setOrden] = useState('-saldo')
  const [busqueda, setBusqueda] = useState('')
  const [detalle, setDetalle] = useState({ results: [], count: 0, saldo_filtrado: 0, porcentaje_sobre_cartera_total: 0 })
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)

  const filtrosClave = JSON.stringify(filtros || {})

  const cargar = useCallback(async (paginaSolicitada) => {
    if (!cargaId) return
    setCargando(true)
    setError(null)
    try {
      const params = limpiarParams({
        ...(filtros || {}),
        fecha_corte: fechaCorte,
        page: paginaSolicitada,
        page_size: pageSize,
        ordering: orden,
        buscar: busqueda,
      })
      const data = await carteraService.obtenerDetalle(cargaId, params)
      setDetalle(data)
      setPagina(paginaSolicitada)
    } catch (e) {
      setError(e.response?.data?.mensaje || 'No se pudo cargar el detalle.')
    } finally {
      setCargando(false)
    }
  }, [cargaId, filtrosClave, fechaCorte, orden, busqueda, pageSize]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (cargaId) cargar(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cargaId, filtrosClave, fechaCorte, orden, busqueda])

  const irAPagina = useCallback((numero) => cargar(numero), [cargar])
  const alternarOrden = useCallback((campo) => {
    setOrden((prev) => (prev === campo ? `-${campo}` : campo))
  }, [])
  const actualizar = useCallback(() => cargar(pagina), [cargar, pagina])

  return {
    detalle, pagina, orden, busqueda, cargando, error,
    irAPagina, setOrden: alternarOrden, setBusqueda, actualizar,
  }
}
