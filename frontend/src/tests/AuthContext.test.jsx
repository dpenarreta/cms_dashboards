import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AuthProvider, useAuth } from '../context/AuthContext'
import * as authService from '../services/authService'
import { getAccessToken, getRefreshToken, setTokens } from '../services/httpClient'

vi.mock('../services/authService', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  logoutAll: vi.fn(),
  me: vi.fn(),
  refreshToken: vi.fn(),
  changePassword: vi.fn(),
}))

function Sonda() {
  const auth = useAuth()
  return (
    <div>
      <div data-testid="estado">
        {auth.isInitializing ? 'INICIALIZANDO' : auth.isAuthenticated ? `AUTENTICADO:${auth.user?.username}` : 'NO_AUTENTICADO'}
      </div>
      {auth.error && <div data-testid="error">{auth.error}</div>}
      <button onClick={() => auth.login({ identifier: 'ana', password: 'Clave-123' })}>login</button>
      <button onClick={() => auth.logout()}>logout</button>
    </div>
  )
}

function renderConProvider() {
  return render(<AuthProvider><Sonda /></AuthProvider>)
}

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('sin token guardado, termina de inicializar como no autenticado', async () => {
    renderConProvider()
    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('NO_AUTENTICADO'))
    expect(authService.me).not.toHaveBeenCalled()
  })

  it('con token guardado y perfil válido, restaura la sesión', async () => {
    setTokens('access-1', 'refresh-1')
    authService.me.mockResolvedValue({ username: 'ana', permissions: ['dashboard.view'] })
    renderConProvider()
    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('AUTENTICADO:ana'))
  })

  it('con token guardado pero inválido, limpia la sesión', async () => {
    setTokens('access-invalido', 'refresh-1')
    authService.me.mockRejectedValue({ response: { status: 401 } })
    renderConProvider()
    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('NO_AUTENTICADO'))
    expect(getAccessToken()).toBeNull()
  })

  it('login exitoso guarda los tokens y el perfil', async () => {
    authService.login.mockResolvedValue({ access: 'nuevo-access', refresh: 'nuevo-refresh' })
    authService.me.mockResolvedValue({ username: 'ana', permissions: [] })

    renderConProvider()
    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('NO_AUTENTICADO'))

    await userEvent.setup().click(screen.getByText('login'))

    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('AUTENTICADO:ana'))
    expect(getAccessToken()).toBe('nuevo-access')
    expect(getRefreshToken()).toBe('nuevo-refresh')
  })

  it('login fallido expone el mensaje de error de cartera (mensaje, no error.message anidado)', async () => {
    authService.login.mockRejectedValue({ response: { data: { mensaje: 'Usuario o contraseña incorrectos.' } } })

    renderConProvider()
    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('NO_AUTENTICADO'))
    await userEvent.setup().click(screen.getByText('login'))

    await waitFor(() => expect(screen.getByTestId('error')).toHaveTextContent('Usuario o contraseña incorrectos.'))
    expect(getAccessToken()).toBeNull()
  })

  it('logout limpia la sesión aunque el backend falle', async () => {
    setTokens('access-1', 'refresh-1')
    authService.me.mockResolvedValue({ username: 'ana', permissions: [] })
    authService.logout.mockRejectedValue(new Error('red caída'))

    renderConProvider()
    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('AUTENTICADO:ana'))

    await userEvent.setup().click(screen.getByText('logout'))

    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('NO_AUTENTICADO'))
    expect(getAccessToken()).toBeNull()
  })
})
