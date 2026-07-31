import authApi from './authApi'

export function getCurrent() {
  return authApi.get('/branding/current').then((r) => r.data)
}

export function getAdmin() {
  return authApi.get('/branding/admin').then((r) => r.data)
}

export function update(data) {
  return authApi.patch('/branding/admin', data).then((r) => r.data)
}

export function reset() {
  return authApi.post('/branding/admin/reset').then((r) => r.data)
}

export function options() {
  return authApi.get('/branding/admin/options').then((r) => r.data)
}
