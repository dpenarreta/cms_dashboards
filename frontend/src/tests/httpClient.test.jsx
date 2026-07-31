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
    Object.defineProperty(window, 'location', { value: { ...window.location, assign: assignSpy }, writable: true })
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
    expect(assignSpy).toHaveBeenCalledWith('/login')
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

  it('si el refresh falla, limpia la sesión y redirige a login', async () => {
    setTokens('access-expirado', 'refresh-invalido')
    axios.post.mockRejectedValue(new Error('refresh token inválido'))

    const config = { url: '/x/y', headers: {} }
    await expect(interceptoresRegistrados.response[0].rejected({ response: { status: 401 }, config })).rejects.toThrow()

    expect(getAccessToken()).toBeNull()
    expect(assignSpy).toHaveBeenCalledWith('/login')
  })
})
