import { beforeEach, describe, expect, it, vi } from 'vitest'

const clienteMock = vi.fn()
const interceptoresRegistrados = { request: [], response: [] }
clienteMock.interceptors = {
  request: { use: (fn) => interceptoresRegistrados.request.push(fn) },
  response: { use: (fulfilled, rejected) => interceptoresRegistrados.response.push({ fulfilled, rejected }) },
}

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => clienteMock),
    post: vi.fn(),
  },
}))

import axios from 'axios'
import { clearTokens, createApiClient, getAccessToken, setTokens } from '../services/httpClient'

describe('httpClient — almacenamiento de tokens', () => {
  beforeEach(() => localStorage.clear())

  it('guarda y recupera el access token', () => {
    setTokens('access-1')
    expect(getAccessToken()).toBe('access-1')
  })

  it('clearTokens elimina el access token', () => {
    setTokens('access-1')
    clearTokens()
    expect(getAccessToken()).toBeNull()
  })

  it('SEC-19: nunca guarda un refresh token en localStorage', () => {
    setTokens('access-1')
    const claves = Object.keys(localStorage)
    expect(claves.some((clave) => clave.includes('refresh'))).toBe(false)
  })

  it('SEC-19: barre los tokens heredados, incluidos los de la aplicación previa a la integración', () => {
    // Encontrados en un navegador real: `skeleton_*`/`skelleton_base_*` seguían ahí aunque ningún
    // código los lee. Son refresh tokens de larga vida al alcance de cualquier XSS.
    localStorage.setItem('cms_dashboards_refresh_token', 'heredado')
    localStorage.setItem('skeleton_refresh_token', 'viejo-1')
    localStorage.setItem('skelleton_base_refresh_token', 'viejo-2')
    localStorage.setItem('skeleton_access_token', 'viejo-3')
    localStorage.setItem('admin-sidebar-colapsado', 'true')

    clearTokens()

    expect(localStorage.getItem('cms_dashboards_refresh_token')).toBeNull()
    expect(localStorage.getItem('skeleton_refresh_token')).toBeNull()
    expect(localStorage.getItem('skelleton_base_refresh_token')).toBeNull()
    expect(localStorage.getItem('skeleton_access_token')).toBeNull()
    // Y no se lleva puesto lo que no es un token.
    expect(localStorage.getItem('admin-sidebar-colapsado')).toBe('true')
  })
})

describe('httpClient — interceptores', () => {
  let assignSpy

  beforeEach(() => {
    localStorage.clear()
    interceptoresRegistrados.request.length = 0
    interceptoresRegistrados.response.length = 0
    clienteMock.mockReset()
    axios.post.mockReset()
    assignSpy = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname: '/app/dashboards/cartera', search: '', assign: assignSpy },
      writable: true,
    })
    createApiClient('/api/x')
  })

  it('adjunta el Authorization header cuando hay access token guardado', () => {
    setTokens('mi-access-token')
    const config = interceptoresRegistrados.request[0]({ headers: {} })
    expect(config.headers.Authorization).toBe('Bearer mi-access-token')
  })

  it('no adjunta Authorization si no hay token guardado', () => {
    const config = interceptoresRegistrados.request[0]({ headers: {} })
    expect(config.headers.Authorization).toBeUndefined()
  })

  it('un error que no es 401 se rechaza sin tocar nada', async () => {
    const error = { response: { status: 500 }, config: { url: '/x/y' } }
    await expect(interceptoresRegistrados.response[0].rejected(error)).rejects.toBe(error)
    expect(axios.post).not.toHaveBeenCalled()
  })

  it('un 401 en un endpoint de auth se rechaza sin intentar refrescar (evita loops)', async () => {
    const error = { response: { status: 401 }, config: { url: '/auth/login' } }
    await expect(interceptoresRegistrados.response[0].rejected(error)).rejects.toBe(error)
    expect(axios.post).not.toHaveBeenCalled()
  })

  it('un 401 ya reintentado redirige a login sin volver a refrescar', async () => {
    setTokens('access-viejo')
    const error = { response: { status: 401 }, config: { url: '/x/y', _reintentadoTrasRefresh: true, headers: {} } }
    await expect(interceptoresRegistrados.response[0].rejected(error)).rejects.toBe(error)
    expect(axios.post).not.toHaveBeenCalled()
    expect(assignSpy).toHaveBeenCalledWith('/login?from=%2Fapp%2Fdashboards%2Fcartera')
    expect(getAccessToken()).toBeNull()
  })

  it('un 401 refresca el access token y reintenta la solicitud original', async () => {
    setTokens('access-expirado')
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo' } })
    clienteMock.mockResolvedValue({ data: 'respuesta-original' })

    const config = { url: '/x/y', headers: {} }
    const resultado = await interceptoresRegistrados.response[0].rejected({ response: { status: 401 }, config })

    expect(axios.post).toHaveBeenCalledWith('/api/auth/token/refresh', {}, { withCredentials: true })
    expect(getAccessToken()).toBe('access-nuevo')
    expect(clienteMock).toHaveBeenCalledWith(expect.objectContaining({ _reintentadoTrasRefresh: true }))
    expect(config.headers.Authorization).toBe('Bearer access-nuevo')
    expect(resultado).toEqual({ data: 'respuesta-original' })
  })

  it('SEC-19: refresca sin mandar el token y pidiendo que viajen las credenciales', async () => {
    // El token va en la cookie `HttpOnly`: mandarlo en el cuerpo exigiría poder leerlo, que es
    // justamente lo que el cambio elimina. `withCredentials` es lo que hace que la cookie se
    // adjunte cuando el backend está en otro origen.
    setTokens('access-expirado')
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo' } })
    clienteMock.mockResolvedValue({ data: 'ok' })

    await interceptoresRegistrados.response[0].rejected({
      response: { status: 401 }, config: { url: '/x/y', headers: {} },
    })

    expect(axios.post).toHaveBeenCalledWith(
      '/api/auth/token/refresh', {}, { withCredentials: true },
    )
  })

  it('SEC-19: tras refrescar no guarda ningún refresh aunque el backend lo devolviera', async () => {
    setTokens('access-expirado')
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo', refresh: 'no-deberia-guardarse' } })
    clienteMock.mockResolvedValue({ data: 'ok' })

    await interceptoresRegistrados.response[0].rejected({
      response: { status: 401 }, config: { url: '/x/y', headers: {} },
    })

    expect(getAccessToken()).toBe('access-nuevo')
    expect(Object.keys(localStorage).some((clave) => clave.includes('refresh'))).toBe(false)
  })

  it('si el refresh falla, limpia la sesión y redirige a login', async () => {
    setTokens('access-expirado')
    axios.post.mockRejectedValue(new Error('refresh token inválido'))

    const config = { url: '/x/y', headers: {} }
    await expect(interceptoresRegistrados.response[0].rejected({ response: { status: 401 }, config })).rejects.toThrow()

    expect(getAccessToken()).toBeNull()
    expect(assignSpy).toHaveBeenCalledWith('/login?from=%2Fapp%2Fdashboards%2Fcartera')
  })
})

describe('httpClient — destino tras expirar la sesión', () => {
  let assignSpy

  function prepararUbicacion({ pathname, search = '' }) {
    localStorage.clear()
    interceptoresRegistrados.request.length = 0
    interceptoresRegistrados.response.length = 0
    clienteMock.mockReset()
    axios.post.mockReset()
    assignSpy = vi.fn()
    Object.defineProperty(window, 'location', {
      value: { ...window.location, pathname, search, assign: assignSpy },
      writable: true,
    })
    createApiClient('/api/cartera')
    // Sin refresh token guardado, el refresco falla de entrada y se dispara el redirect.
    setTokens('access-expirado')
  }

  it('conserva la ruta y la query en el parámetro from', async () => {
    prepararUbicacion({ pathname: '/app/dashboards/cartera', search: '?fecha_corte=2026-08-31' })

    await expect(
      interceptoresRegistrados.response[0].rejected({ response: { status: 401 }, config: { url: '/x', headers: {} } }),
    ).rejects.toBeDefined()

    expect(assignSpy).toHaveBeenCalledWith(
      '/login?from=%2Fapp%2Fdashboards%2Fcartera%3Ffecha_corte%3D2026-08-31',
    )
  })

  it('no agrega from si ya está en /login (evitaría apuntarse a sí mismo)', async () => {
    prepararUbicacion({ pathname: '/login' })

    await expect(
      interceptoresRegistrados.response[0].rejected({ response: { status: 401 }, config: { url: '/x', headers: {} } }),
    ).rejects.toBeDefined()

    expect(assignSpy).toHaveBeenCalledWith('/login')
  })
})
