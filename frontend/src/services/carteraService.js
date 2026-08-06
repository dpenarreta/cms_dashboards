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

export function sugerirMapeoPlantilla(cargaId, aliases, valoresBlancos) {
  return api.post('/plantilla/sugerir', { carga_id: cargaId, aliases, valores_blancos: valoresBlancos }).then((r) => r.data)
}

export function previsualizarMapeoPlantilla(cargaId, mapeo, aliases, valoresBlancos) {
  return api.post('/plantilla/previsualizar', { carga_id: cargaId, mapeo, aliases, valores_blancos: valoresBlancos }).then((r) => r.data)
}

export function aplicarMapeoPlantilla(cargaId, mapeo, aliases, valoresBlancos, columnasHistoricas) {
  return api.post('/plantilla/aplicar', {
    carga_id: cargaId, mapeo, aliases, valores_blancos: valoresBlancos, columnas_historicas: columnasHistoricas,
  }).then((r) => r.data)
}

export function obtenerValoresColumnaPlantilla(cargaId, columna, aliases, valoresBlancos) {
  return api.post('/plantilla/valores-columna', { carga_id: cargaId, columna, aliases, valores_blancos: valoresBlancos }).then((r) => r.data)
}

export function obtenerArchivoActualDashboard(dashboardId) {
  return api.post('/plantilla/archivo-actual', { dashboard_id: dashboardId }).then((r) => r.data)
}

/** Agrega UN componente nuevo a la "Zona Personal" del dashboard — reutiliza el endpoint legado
 * `POST /agregar-grafica` (`services/dashboard_layout.py::agregar_componente_generado`), fijando
 * siempre `zona: 'personal'` para que quede marcado y agrupado aparte (`config.zona`, ver
 * `EditableGrid.jsx`). A diferencia del resto del editor de dashboard, esto persiste de inmediato
 * (no pasa por el borrador ni "Guardar cambios") — el llamador debe refrescar el layout después
 * (`useDashboardLayout().recargar()`). */
export function agregarComponentePersonal(payload) {
  return api.post('/agregar-grafica', { ...payload, zona: 'personal' }).then((r) => r.data)
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
