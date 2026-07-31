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
