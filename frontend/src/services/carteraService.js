import api from './api'

export function validarArchivo(archivo, hoja) {
  const formData = new FormData()
  formData.append('archivo', archivo)
  if (hoja) formData.append('hoja', hoja)
  return api.post('/validar-archivo', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
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
