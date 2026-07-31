import authApi from './authApi'

export function catalog() {
  return authApi.get('/permissions/').then((r) => r.data)
}
