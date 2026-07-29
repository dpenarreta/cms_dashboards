import axios from 'axios'

const api = axios.create({ baseURL: '/api/dashboards' })

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
