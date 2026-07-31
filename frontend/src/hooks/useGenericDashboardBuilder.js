import { useCallback, useRef, useState } from 'react'
import * as carteraService from '../services/carteraService'
import { descripcionRecomendacion, tituloRecomendacion } from '../utils/chartRecommendations'

const FASE = {
  CARGA: 'CARGA',
  ALIAS: 'ALIAS',
  RECOMENDACIONES: 'RECOMENDACIONES',
}

/**
 * Flujo "cargar archivo → reconocer columnas y confirmar alias → recomendar gráficas → agregar
 * una por una": reemplaza el armado manual de gráficas (elegir columnas y escribir un título a
 * mano) por recomendaciones que el sistema arma solo, que el usuario aprueba con "Agregar" — cada
 * "Agregar" queda incluido en el dashboard de inmediato, no hace falta un paso final de "generar".
 */
export function useGenericDashboardBuilder(dashboardId) {
  const [fase, setFase] = useState(FASE.CARGA)
  const [archivoInfo, setArchivoInfo] = useState(null)
  const [columnas, setColumnas] = useState([])
  const [aliases, setAliases] = useState({})
  const [utilizables, setUtilizables] = useState({})
  const [recomendaciones, setRecomendaciones] = useState([])
  const [agregadas, setAgregadas] = useState(() => new Set())
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const archivoLocalRef = useRef(null)
  // La primera gráfica que se agrega tras cargar un archivo nuevo debe reemplazar lo que ya
  // hubiera en el dashboard (para no mezclar datos de dos archivos distintos); las siguientes,
  // dentro de la misma sesión de recomendaciones, se suman.
  const esPrimeraGraficaRef = useRef(true)

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
        totalFilas: data.total_filas_detectadas,
        hojasDisponibles: data.hojas_disponibles,
        hojaSeleccionada: data.hoja_seleccionada,
      })
      const analisis = await carteraService.analizarColumnas(data.carga_id)
      setColumnas(analisis.columnas)
      // El análisis automático es solo una sugerencia: ninguna columna se quita ni se oculta —
      // todas se muestran, precargadas con la sugerencia del sistema, pero el usuario decide con
      // el checkmark cuál usar.
      const aliasesIniciales = {}
      const utilizablesIniciales = {}
      for (const columna of analisis.columnas) {
        aliasesIniciales[columna.nombre] = columna.nombre
        utilizablesIniciales[columna.nombre] = columna.apta_para_valor || columna.apta_para_categoria
      }
      setAliases(aliasesIniciales)
      setUtilizables(utilizablesIniciales)
      setRecomendaciones([])
      setAgregadas(new Set())
      esPrimeraGraficaRef.current = true
      setFase(FASE.ALIAS)
    } catch (e) {
      setError(e.response?.data?.mensaje || 'No se pudo analizar el archivo.')
    } finally {
      setCargando(false)
    }
  }, [dashboardId])

  const cambiarHoja = useCallback(async (hoja) => {
    if (!archivoLocalRef.current) return
    await subirYValidar(archivoLocalRef.current, hoja)
  }, [subirYValidar])

  const actualizarAlias = useCallback((columna, alias) => {
    setAliases((prev) => ({ ...prev, [columna]: alias }))
  }, [])

  const actualizarUtilizable = useCallback((columna, valor) => {
    setUtilizables((prev) => ({ ...prev, [columna]: valor }))
  }, [])

  const confirmarAliases = useCallback(async () => {
    if (!archivoInfo?.cargaId) return
    setCargando(true)
    setError(null)
    try {
      const columnasUtilizables = Object.keys(utilizables).filter((nombre) => utilizables[nombre])
      const data = await carteraService.recomendarGraficas(archivoInfo.cargaId, columnasUtilizables)
      setRecomendaciones(data.recomendaciones)
      setFase(FASE.RECOMENDACIONES)
    } catch (e) {
      setError(e.response?.data?.mensaje || 'No se pudieron generar recomendaciones.')
    } finally {
      setCargando(false)
    }
  }, [archivoInfo, utilizables])

  /**
   * Vuelve al paso de columnas/alias sin perder nada: ni el archivo ya subido, ni los alias y
   * checkmarks ya elegidos, ni las gráficas que ya se hayan agregado en esta sesión (sus ids son
   * deterministas — `titulo_recomendacion`/`generar_recomendaciones` — así que si el usuario
   * vuelve a "Continuar" sin cambiar nada, las mismas recomendaciones aparecen como ya agregadas).
   */
  const volverAAlias = useCallback(() => {
    setError(null)
    setFase(FASE.ALIAS)
  }, [])

  const agregarGrafica = useCallback(async (recomendacion, tipoVisualizacion) => {
    if (!archivoInfo?.cargaId) return { ok: false }
    setCargando(true)
    setError(null)
    try {
      await carteraService.agregarGrafica(archivoInfo.cargaId, {
        titulo: tituloRecomendacion(recomendacion, aliases),
        descripcion: descripcionRecomendacion(recomendacion, aliases),
        columnaValor: recomendacion.columna_valor,
        columnaCategoria: recomendacion.columna_categoria,
        columnaSerie: recomendacion.columna_serie_sugerida,
        columnaValorY: recomendacion.columna_valor_y,
        tipoVisualizacion,
        reemplazarExistentes: esPrimeraGraficaRef.current,
      })
      esPrimeraGraficaRef.current = false
      setAgregadas((prev) => new Set(prev).add(recomendacion.id))
      return { ok: true }
    } catch (e) {
      setError(e.response?.data?.mensaje || 'No se pudo agregar la gráfica.')
      return { ok: false }
    } finally {
      setCargando(false)
    }
  }, [archivoInfo, aliases])

  const limpiar = useCallback(async () => {
    if (archivoInfo?.cargaId) {
      try { await carteraService.eliminarArchivo(archivoInfo.cargaId) } catch { /* noop */ }
    }
    setFase(FASE.CARGA)
    setArchivoInfo(null)
    setColumnas([])
    setAliases({})
    setUtilizables({})
    setRecomendaciones([])
    setAgregadas(new Set())
    setError(null)
    archivoLocalRef.current = null
  }, [archivoInfo])

  return {
    FASE,
    fase,
    archivoInfo,
    columnas,
    aliases,
    utilizables,
    recomendaciones,
    agregadas,
    cargando,
    error,
    subirYValidar,
    cambiarHoja,
    actualizarAlias,
    actualizarUtilizable,
    confirmarAliases,
    volverAAlias,
    agregarGrafica,
    limpiar,
  }
}
