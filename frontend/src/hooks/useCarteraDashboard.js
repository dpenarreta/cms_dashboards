import { useCallback, useRef, useState } from 'react'
import * as carteraService from '../services/carteraService'

const FASE = {
  CARGA: 'CARGA',
  MAPEO: 'MAPEO',
  DASHBOARD: 'DASHBOARD',
}

const FILTROS_INICIALES = {
  cliente: '', ciudad: '', zona: '', sucursal: '', recuperador: '', causal: '',
  estado_cartera: '', rango_mora: '', producto: '', articulo: '', tipo_venta: '', estado_cliente: '',
  fecha_vencimiento_desde: '', fecha_vencimiento_hasta: '', fecha_emision_desde: '', fecha_emision_hasta: '',
}

export function useCarteraDashboard(dashboardId) {
  const [fase, setFase] = useState(FASE.CARGA)
  const [archivoInfo, setArchivoInfo] = useState(null)
  const [mapeoSugerido, setMapeoSugerido] = useState(null)
  const [mapeoConfirmado, setMapeoConfirmado] = useState({})
  const [previewFilas, setPreviewFilas] = useState([])
  const [fechaCorte, setFechaCorte] = useState('')
  const [filtrosAplicados, setFiltrosAplicados] = useState(FILTROS_INICIALES)
  const [filtrosBorrador, setFiltrosBorrador] = useState(FILTROS_INICIALES)

  const [kpis, setKpis] = useState(null)
  const [topClientes, setTopClientes] = useState([])
  const [paretoCiudades, setParetoCiudades] = useState({ ciudades: [], total_vencida: 0 })
  const [recuperadores, setRecuperadores] = useState([])
  const [causales, setCausales] = useState(null)
  const [recuperadorCausalChart, setRecuperadorCausalChart] = useState([])
  const [recuperadorCausalMatriz, setRecuperadorCausalMatriz] = useState(null)
  const [metricaRecuperadorCausal, setMetricaRecuperadorCausal] = useState('saldo')

  const [resumenValidacion, setResumenValidacion] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const archivoLocalRef = useRef(null)

  const paramsBase = useCallback((extra = {}) => {
    const params = { ...filtrosAplicados, ...extra }
    if (fechaCorte) params.fecha_corte = fechaCorte
    Object.keys(params).forEach((k) => { if (!params[k]) delete params[k] })
    return params
  }, [filtrosAplicados, fechaCorte])

  const subirYValidar = useCallback(async (archivo, hoja) => {
    setCargando(true)
    setError(null)
    archivoLocalRef.current = archivo
    try {
      const data = await carteraService.validarArchivo(archivo, hoja, dashboardId)
      setArchivoInfo({
        cargaId: data.carga_id,
        nombreArchivo: data.nombre_archivo,
        tamanoBytes: data.tamano_bytes,
        fechaCarga: data.fecha_carga,
        hojasDisponibles: data.hojas_disponibles,
        hojaSeleccionada: data.hoja_seleccionada,
        totalFilas: data.total_filas_detectadas,
      })
      setMapeoSugerido(data.mapeo_sugerido)
      setPreviewFilas(data.preview)

      const inicial = {}
      for (const campo of [...data.mapeo_sugerido.obligatorios, ...data.mapeo_sugerido.opcionales]) {
        inicial[campo.campo] = campo.columna_detectada || ''
      }
      setMapeoConfirmado(inicial)
      setFase(FASE.MAPEO)
    } catch (e) {
      setError(e.response?.data?.mensaje || 'No se pudo validar el archivo.')
    } finally {
      setCargando(false)
    }
  }, [dashboardId])

  const cambiarHoja = useCallback(async (hoja) => {
    if (!archivoLocalRef.current) return
    await subirYValidar(archivoLocalRef.current, hoja)
  }, [subirYValidar])

  const actualizarMapeo = useCallback((campo, columna) => {
    setMapeoConfirmado((prev) => ({ ...prev, [campo]: columna }))
  }, [])

  const refrescarDashboard = useCallback(async (cargaId, fc, filtrosOverride) => {
    setCargando(true)
    try {
      const params = { ...(filtrosOverride || filtrosAplicados) }
      if (fc) params.fecha_corte = fc
      Object.keys(params).forEach((k) => { if (!params[k]) delete params[k] })

      const [r1, r2, r3, r4, r5] = await Promise.all([
        carteraService.obtenerResumen(cargaId, params),
        carteraService.obtenerTopClientes(cargaId, params),
        carteraService.obtenerParetoCiudades(cargaId, params),
        carteraService.obtenerRecuperadores(cargaId, params),
        carteraService.obtenerCausales(cargaId, params),
      ])
      setKpis(r1)
      setTopClientes(r2)
      setParetoCiudades(r3)
      setRecuperadores(r4)
      setCausales(r5)

      const r6 = await carteraService.obtenerRecuperadoresCausales(cargaId, { ...params, metrica: metricaRecuperadorCausal })
      setRecuperadorCausalChart(r6.chart)
      setRecuperadorCausalMatriz(r6.matriz)
    } catch (e) {
      setError(e.response?.data?.mensaje || 'No se pudo cargar el dashboard.')
    } finally {
      setCargando(false)
    }
  }, [filtrosAplicados, metricaRecuperadorCausal])

  const procesar = useCallback(async () => {
    if (!archivoInfo) return
    setCargando(true)
    setError(null)
    try {
      const data = await carteraService.procesarArchivo({
        cargaId: archivoInfo.cargaId,
        mapeo: mapeoConfirmado,
        fechaCorte: fechaCorte || undefined,
        hoja: archivoInfo.hojaSeleccionada,
      })
      setKpis(data)
      setFechaCorte(data.fecha_corte)
      setResumenValidacion(data.resumen_validacion)
      setFase(FASE.DASHBOARD)
      await refrescarDashboard(archivoInfo.cargaId, data.fecha_corte)
    } catch (e) {
      setError(e.response?.data?.mensaje || 'No se pudo procesar el archivo.')
    } finally {
      setCargando(false)
    }
  }, [archivoInfo, mapeoConfirmado, fechaCorte, refrescarDashboard])

  const limpiar = useCallback(async () => {
    if (archivoInfo?.cargaId) {
      try { await carteraService.eliminarArchivo(archivoInfo.cargaId) } catch { /* noop */ }
    }
    setFase(FASE.CARGA)
    setArchivoInfo(null)
    setMapeoSugerido(null)
    setMapeoConfirmado({})
    setPreviewFilas([])
    setFechaCorte('')
    setFiltrosAplicados(FILTROS_INICIALES)
    setFiltrosBorrador(FILTROS_INICIALES)
    setKpis(null)
    setTopClientes([])
    setParetoCiudades({ ciudades: [], total_vencida: 0 })
    setRecuperadores([])
    setCausales(null)
    setRecuperadorCausalChart([])
    setRecuperadorCausalMatriz(null)
    setResumenValidacion(null)
    setError(null)
    archivoLocalRef.current = null
  }, [archivoInfo])

  const actualizarFiltroBorrador = useCallback((campo, valor) => {
    setFiltrosBorrador((prev) => ({ ...prev, [campo]: valor }))
  }, [])

  const aplicarFiltros = useCallback(async () => {
    setFiltrosAplicados(filtrosBorrador)
    if (archivoInfo?.cargaId) {
      await refrescarDashboard(archivoInfo.cargaId, fechaCorte, filtrosBorrador)
    }
  }, [filtrosBorrador, archivoInfo, fechaCorte, refrescarDashboard])

  const limpiarFiltros = useCallback(async () => {
    setFiltrosBorrador(FILTROS_INICIALES)
    setFiltrosAplicados(FILTROS_INICIALES)
    if (archivoInfo?.cargaId) {
      await refrescarDashboard(archivoInfo.cargaId, fechaCorte, FILTROS_INICIALES)
    }
  }, [archivoInfo, fechaCorte, refrescarDashboard])

  const cambiarFechaCorte = useCallback(async (nuevaFecha) => {
    setFechaCorte(nuevaFecha)
    if (archivoInfo?.cargaId) {
      await refrescarDashboard(archivoInfo.cargaId, nuevaFecha, filtrosAplicados)
    }
  }, [archivoInfo, filtrosAplicados, refrescarDashboard])

  const cambiarMetricaRecuperadorCausal = useCallback(async (metrica) => {
    setMetricaRecuperadorCausal(metrica)
    if (!archivoInfo?.cargaId) return
    const data = await carteraService.obtenerRecuperadoresCausales(archivoInfo.cargaId, { ...paramsBase(), metrica })
    setRecuperadorCausalChart(data.chart)
    setRecuperadorCausalMatriz(data.matriz)
  }, [archivoInfo, paramsBase])

  return {
    FASE,
    fase,
    archivoInfo,
    mapeoSugerido,
    mapeoConfirmado,
    previewFilas,
    fechaCorte,
    filtrosBorrador,
    filtrosAplicados,
    kpis,
    topClientes,
    paretoCiudades,
    recuperadores,
    causales,
    recuperadorCausalChart,
    recuperadorCausalMatriz,
    metricaRecuperadorCausal,
    resumenValidacion,
    cargando,
    error,
    subirYValidar,
    cambiarHoja,
    actualizarMapeo,
    procesar,
    limpiar,
    actualizarFiltroBorrador,
    aplicarFiltros,
    limpiarFiltros,
    cambiarFechaCorte,
    cambiarMetricaRecuperadorCausal,
    refrescarDashboard,
    paramsBase,
  }
}
