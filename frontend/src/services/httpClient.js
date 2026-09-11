import axios from 'axios'

// Origen del backend. Vacío = mismo origen que el frontend, que es el caso en desarrollo (el
// proxy de Vite reenvía `/api` a :8000) y en un despliegue donde nginx sirve ambos. Se puede
// apuntar a otro host con `VITE_API_BASE_URL` sin tocar código, en vez de tener el prefijo
// escrito a mano en cada cliente.
const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '')

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
  // Se respeta `API_BASE_URL` como cualquier otro cliente: antes era un
  // `axios.post('/api/auth/token/refresh')` con el prefijo escrito a mano, así que el refresco
  // era lo único que dejaba de funcionar si el backend no está en el mismo origen. Se llama a
  // `axios.post` directo y no a un cliente creado con `createApiClient` a propósito: ese trae el
  // interceptor de 401 y un fallo acá dispararía otro refresco en cascada.
  const { data } = await axios.post(`${API_BASE_URL}/api/auth/token/refresh`, { refresh })
  // El backend rota el refresh token en cada refresco (`ROTATE_REFRESH_TOKENS`), así que hay que
  // guardar el nuevo: conservar el viejo lo dejaría inservible en el próximo refresco y —peor— el
  // backend lo interpretaría como reutilización de un token robado y revocaría la sesión entera.
  // `data.refresh` puede no venir si el backend todavía no rota; en ese caso se conserva el actual.
  setTokens(data.access, data.refresh || refresh)
  return data.access
}

function redirigirALogin() {
  clearTokens()
  if (typeof window === 'undefined') return
  // Se conserva a dónde iba el usuario. Este redirect es una recarga completa del documento (no
  // pasa por React Router), así que el `state.from` que arma `RequirePermission` se pierde: sin
  // esto, a quien se le vencía la sesión en medio de un dashboard lo devolvíamos al listado por
  // defecto en vez de a la pantalla en la que estaba. Va como query param porque es lo único que
  // sobrevive a una recarga; solo la ruta, nunca datos del usuario.
  const destino = window.location.pathname + window.location.search
  const yaEstaEnLogin = window.location.pathname === '/login'
  window.location.assign(
    yaEstaEnLogin ? '/login' : `/login?from=${encodeURIComponent(destino)}`,
  )
}

/**
 * Crea un cliente Axios con interceptores de sesión: adjunta el access token en cada solicitud y,
 * ante un 401 (fuera de los endpoints de auth), intenta refrescar una sola vez y reintentar la
 * solicitud original. Si el refresh también falla, limpia la sesión y redirige a /login.
 */
export function createApiClient(prefijo) {
  const cliente = axios.create({ baseURL: `${API_BASE_URL}${prefijo}` })

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
