import { createApiClient } from './httpClient'

const api = createApiClient('/api/dashboards')

export function obtenerLayout(dashboardId) {
  return api.get(`/${dashboardId}/layout`).then((r) => r.data)
}

export function guardarLayout(dashboardId, { version, components, changedBy }) {
  return api.put(`/${dashboardId}/layout`, { version, components, changed_by: changedBy }).then((r) => r.data)
}

export function restablecerLayout(dashboardId, { changedBy }) {
  return api.post(`/${dashboardId}/layout/reset`, { changed_by: changedBy }).then((r) => r.data)
}

/** Agrega un componente de solo presentación (título o separador, panel lateral de componentes)
 * — a diferencia del resto de acciones del editor, persiste de inmediato (no pasa por el
 * borrador ni por "Guardar cambios"), igual que `carteraService.agregarComponentePersonal`. */
export function agregarComponentePresentacional(dashboardId, { tipo, anchoColumnas, zona }) {
  return api.post(`/${dashboardId}/componentes-presentacionales`, {
    tipo, ancho_columnas: anchoColumnas, zona,
  }).then((r) => r.data)
}

export function obtenerVersiones(dashboardId) {
  return api.get(`/${dashboardId}/versions`).then((r) => r.data)
}

export function obtenerDashboardsAutorizados() {
  return api.get('/authorized').then((r) => r.data)
}

export function crearDashboard({ name, area, description }) {
  return api.post('/', { name, area, description }).then((r) => r.data)
}

export function actualizarDashboard(dashboardId, { name, area }) {
  return api.patch(`/${dashboardId}/`, { name, area }).then((r) => r.data)
}

export function eliminarDashboard(dashboardId, confirmationName) {
  return api.delete(`/${dashboardId}/`, { data: { confirmation_name: confirmationName } }).then((r) => r.data)
}

export function obtenerPestanas(dashboardId) {
  return api.get(`/${dashboardId}/pestanas`).then((r) => r.data)
}

export function crearPestana(dashboardId, { name }) {
  return api.post(`/${dashboardId}/pestanas`, { name }).then((r) => r.data)
}

export function obtenerAcceso(dashboardId) {
  return api.get(`/${dashboardId}/acceso`).then((r) => r.data)
}

export function actualizarAcceso(dashboardId, { rolesEditores, rolesLectores }) {
  return api.put(`/${dashboardId}/acceso`, { roles_editores: rolesEditores, roles_lectores: rolesLectores }).then((r) => r.data)
}

export function reasignarDueno(dashboardId, ownerId) {
  return api.patch(`/${dashboardId}/dueno`, { owner_id: ownerId }).then((r) => r.data)
}
