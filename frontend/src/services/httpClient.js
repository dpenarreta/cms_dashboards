import axios from 'axios'

const ACCESS_TOKEN_KEY = 'cms_dashboards_access_token'
const REFRESH_TOKEN_KEY = 'cms_dashboards_refresh_token'

// Endpoints de autenticación: nunca deben disparar el refresh automático en un 401 (evitaría
// loops si las credenciales o el propio refresh token son inválidos).
const AUTH_ENDPOINTS = ['/auth/login', '/auth/token/refresh', '/auth/logout']

export function setTokens(access, refresh) {
  if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access)
  else localStorage.removeItem(ACCESS_TOKEN_KEY)
  if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
  else localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function clearTokens() {
  setTokens(null, null)
}

function esEndpointDeAuth(url) {
  return AUTH_ENDPOINTS.some((endpoint) => url?.includes(endpoint))
}

let refreshPendiente = null

async function refrescarAccessToken() {
  const refresh = getRefreshToken()
  if (!refresh) throw new Error('No hay sesión activa.')
  const { data } = await axios.post('/api/auth/token/refresh', { refresh })
  setTokens(data.access, refresh)
  return data.access
}

function redirigirALogin() {
  clearTokens()
  if (typeof window !== 'undefined') window.location.assign('/login')
}

/**
 * Crea un cliente Axios con interceptores de sesión: adjunta el access token en cada solicitud y,
 * ante un 401 (fuera de los endpoints de auth), intenta refrescar una sola vez y reintentar la
 * solicitud original. Si el refresh también falla, limpia la sesión y redirige a /login.
 */
export function createApiClient(baseURL) {
  const cliente = axios.create({ baseURL })

  cliente.interceptors.request.use((config) => {
    const token = getAccessToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  cliente.interceptors.response.use(
    (response) => response,
    async (error) => {
      const { config, response } = error
      if (!response || response.status !== 401 || !config || esEndpointDeAuth(config.url)) {
        return Promise.reject(error)
      }
      if (config._reintentadoTrasRefresh) {
        redirigirALogin()
        return Promise.reject(error)
      }
      config._reintentadoTrasRefresh = true
      try {
        refreshPendiente = refreshPendiente || refrescarAccessToken()
        const nuevoAccess = await refreshPendiente
        refreshPendiente = null
        config.headers.Authorization = `Bearer ${nuevoAccess}`
        return cliente(config)
      } catch (refreshError) {
        refreshPendiente = null
        redirigirALogin()
        return Promise.reject(refreshError)
      }
    },
  )

  return cliente
}
