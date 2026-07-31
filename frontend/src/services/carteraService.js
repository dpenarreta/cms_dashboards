import api from './api'

export function validarArchivo(archivo, hoja, dashboardId) {
  const formData = new FormData()
  formData.append('archivo', archivo)
  if (hoja) formData.append('hoja', hoja)
  if (dashboardId) formData.append('dashboard_id', dashboardId)
  return api.post('/validar-archivo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export function analizarColumnas(cargaId) {
  return api.post('/analizar-columnas', { carga_id: cargaId }).then((r) => r.data)
}

export function recomendarGraficas(cargaId, columnasUtilizables) {
  return api.post('/recomendar-graficas', {
    carga_id: cargaId,
    columnas_utilizables: columnasUtilizables,
  }).then((r) => r.data)
}

export function agregarGrafica(cargaId, {
  titulo, descripcion, columnaValor, columnaCategoria, columnaSerie, columnaValorY, tipoVisualizacion, reemplazarExistentes,
}) {
  return api.post('/agregar-grafica', {
    carga_id: cargaId,
    titulo,
    descripcion: descripcion || undefined,
    columna_valor: columnaValor,
    columna_categoria: columnaCategoria || undefined,
    columna_serie: columnaSerie || undefined,
    columna_valor_y: columnaValorY || undefined,
    tipo_visualizacion: tipoVisualizacion || undefined,
    reemplazar_existentes: Boolean(reemplazarExistentes),
  }).then((r) => r.data)
}

export function procesarArchivo({ cargaId, mapeo, fechaCorte, hoja }) {
  return api.post('/procesar', {
    carga_id: cargaId,
    mapeo,
    fecha_corte: fechaCorte || undefined,
    hoja: hoja || undefined,
  }).then((r) => r.data)
}

export function obtenerResumen(cargaId, params) {
  return api.get(`/resumen/${cargaId}`, { params }).then((r) => r.data)
}

export function obtenerTopClientes(cargaId, params) {
  return api.get(`/top-clientes/${cargaId}`, { params }).then((r) => r.data)
}

export function obtenerParetoCiudades(cargaId, params) {
  return api.get(`/pareto-ciudades/${cargaId}`, { params }).then((r) => r.data)
}

export function obtenerRecuperadores(cargaId, params) {
  return api.get(`/recuperadores/${cargaId}`, { params }).then((r) => r.data)
}

export function obtenerCausales(cargaId, params) {
  return api.get(`/causales/${cargaId}`, { params }).then((r) => r.data)
}

export function obtenerRecuperadoresCausales(cargaId, params) {
  return api.get(`/recuperadores-causales/${cargaId}`, { params }).then((r) => r.data)
}

export function obtenerDetalle(cargaId, params) {
  return api.get(`/detalle/${cargaId}`, { params }).then((r) => r.data)
}

export function urlExportar(cargaId, params) {
  const query = new URLSearchParams(params).toString()
  return `/api/cartera/exportar/${cargaId}${query ? `?${query}` : ''}`
}

export function eliminarArchivo(cargaId) {
  return api.delete(`/archivo/${cargaId}`)
}
