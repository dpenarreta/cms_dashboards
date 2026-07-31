import authApi from './authApi'

export function list(params) {
  return authApi.get('/roles/', { params }).then((r) => r.data)
}

export function get(id) {
  return authApi.get(`/roles/${id}/`).then((r) => r.data)
}

export function create(data) {
  return authApi.post('/roles/', data).then((r) => r.data)
}

export function update(id, data) {
  return authApi.patch(`/roles/${id}/`, data).then((r) => r.data)
}

export function remove(id) {
  return authApi.delete(`/roles/${id}/`).then((r) => r.data)
}

export function permissionsCatalog() {
  return authApi.get('/roles/permissions-catalog/').then((r) => r.data)
}
