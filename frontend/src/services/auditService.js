import authApi from './authApi'

export function list(params) {
  return authApi.get('/audit/', { params }).then((r) => r.data)
}

export function get(id) {
  return authApi.get(`/audit/${id}/`).then((r) => r.data)
}

export function exportCsv(params) {
  return authApi.get('/audit/export/', { params, responseType: 'blob' }).then((r) => r.data)
}
