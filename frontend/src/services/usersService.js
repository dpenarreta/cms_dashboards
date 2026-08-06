import authApi from './authApi'

export function list(params) {
  return authApi.get('/users/', { params }).then((r) => r.data)
}

export function get(id) {
  return authApi.get(`/users/${id}/`).then((r) => r.data)
}

export function create(data) {
  return authApi.post('/users/', data).then((r) => r.data)
}

export function update(id, data) {
  return authApi.patch(`/users/${id}/`, data).then((r) => r.data)
}

export function enable(id) {
  return authApi.post(`/users/${id}/enable/`).then((r) => r.data)
}

export function disable(id) {
  return authApi.post(`/users/${id}/disable/`).then((r) => r.data)
}

export function block(id) {
  return authApi.post(`/users/${id}/block/`).then((r) => r.data)
}

export function unblock(id) {
  return authApi.post(`/users/${id}/unblock/`).then((r) => r.data)
}

export function assignRoles(id, roleIds) {
  return authApi.post(`/users/${id}/roles/`, { role_ids: roleIds }).then((r) => r.data)
}

export function assignPermissions(id, codenames) {
  return authApi.post(`/users/${id}/permissions/`, { codenames }).then((r) => r.data)
}

export function setSuperuser(id, isSuperuser) {
  return authApi.post(`/users/${id}/superuser/`, { is_superuser: isSuperuser }).then((r) => r.data)
}

export function resetPassword(id) {
  return authApi.post(`/users/${id}/reset_password/`).then((r) => r.data)
}
