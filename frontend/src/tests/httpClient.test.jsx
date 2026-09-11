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
import { clearTokens, createApiClient, getAccessToken, getRefreshToken, setTokens } from '../services/httpClient'

describe('httpClient — almacenamiento de tokens', () => {
  beforeEach(() => localStorage.clear())

  it('guarda y recupera access/refresh token', () => {
    setTokens('access-1', 'refresh-1')
    expect(getAccessToken()).toBe('access-1')
    expect(getRefreshToken()).toBe('refresh-1')
  })

  it('clearTokens elimina ambos tokens', () => {
    setTokens('access-1', 'refresh-1')
    clearTokens()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
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
    setTokens('mi-access-token', 'mi-refresh-token')
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
    setTokens('access-viejo', 'refresh-viejo')
    const error = { response: { status: 401 }, config: { url: '/x/y', _reintentadoTrasRefresh: true, headers: {} } }
    await expect(interceptoresRegistrados.response[0].rejected(error)).rejects.toBe(error)
    expect(axios.post).not.toHaveBeenCalled()
    expect(assignSpy).toHaveBeenCalledWith('/login?from=%2Fapp%2Fdashboards%2Fcartera')
    expect(getAccessToken()).toBeNull()
  })

  it('un 401 refresca el access token y reintenta la solicitud original', async () => {
    setTokens('access-expirado', 'refresh-valido')
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo' } })
    clienteMock.mockResolvedValue({ data: 'respuesta-original' })

    const config = { url: '/x/y', headers: {} }
    const resultado = await interceptoresRegistrados.response[0].rejected({ response: { status: 401 }, config })

    expect(axios.post).toHaveBeenCalledWith('/api/auth/token/refresh', { refresh: 'refresh-valido' })
    expect(getAccessToken()).toBe('access-nuevo')
    expect(clienteMock).toHaveBeenCalledWith(expect.objectContaining({ _reintentadoTrasRefresh: true }))
    expect(config.headers.Authorization).toBe('Bearer access-nuevo')
    expect(resultado).toEqual({ data: 'respuesta-original' })
  })

  it('guarda el refresh token rotado que devuelve el backend', async () => {
    // El backend rota el refresh en cada refresco (`ROTATE_REFRESH_TOKENS`). Conservar el viejo
    // lo dejaría inservible y —peor— el backend lo leería como reutilización de un token robado
    // y revocaría la sesión completa.
    setTokens('access-expirado', 'refresh-viejo')
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo', refresh: 'refresh-rotado' } })
    clienteMock.mockResolvedValue({ data: 'ok' })

    await interceptoresRegistrados.response[0].rejected({
      response: { status: 401 }, config: { url: '/x/y', headers: {} },
    })

    expect(getRefreshToken()).toBe('refresh-rotado')
  })

  it('si el backend no devuelve refresh nuevo, conserva el actual', async () => {
    setTokens('access-expirado', 'refresh-valido')
    axios.post.mockResolvedValue({ data: { access: 'access-nuevo' } })
    clienteMock.mockResolvedValue({ data: 'ok' })

    await interceptoresRegistrados.response[0].rejected({
      response: { status: 401 }, config: { url: '/x/y', headers: {} },
    })

    expect(getRefreshToken()).toBe('refresh-valido')
  })

  it('si el refresh falla, limpia la sesión y redirige a login', async () => {
    setTokens('access-expirado', 'refresh-invalido')
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
    setTokens('access-expirado', null)
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
