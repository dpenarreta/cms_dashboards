import api from './api'

export function obtenerLayout() {
  return api.get('/plantilla-base/layout').then((r) => r.data)
}

export function guardarLayout({ version, components, changedBy }) {
  return api.put('/plantilla-base/layout', { version, components, changed_by: changedBy }).then((r) => r.data)
}

export function restablecer() {
  return api.post('/plantilla-base/reset').then((r) => r.data)
}
