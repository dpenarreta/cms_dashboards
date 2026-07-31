import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LoginPage from '../pages/authentication/LoginPage'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/app/dashboards/cartera" element={<div>pagina-dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  it('si ya está autenticado, redirige al dashboard sin mostrar el formulario', () => {
    useAuth.mockReturnValue({ isAuthenticated: true, login: vi.fn() })
    renderLogin()
    expect(screen.getByText('pagina-dashboard')).toBeInTheDocument()
  })

  it('envía usuario y contraseña al iniciar sesión', async () => {
    const login = vi.fn().mockResolvedValue({ ok: true })
    useAuth.mockReturnValue({ isAuthenticated: false, login })
    renderLogin()

    await userEvent.type(screen.getByLabelText('Usuario o correo'), 'ana')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Segura-123')
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))

    expect(login).toHaveBeenCalledWith({ identifier: 'ana', password: 'Clave-Segura-123' })
    await waitFor(() => expect(screen.getByText('pagina-dashboard')).toBeInTheDocument())
  })

  it('muestra el mensaje de error cuando el login falla', async () => {
    const login = vi.fn().mockResolvedValue({ ok: false, error: 'Usuario o contraseña incorrectos.' })
    useAuth.mockReturnValue({ isAuthenticated: false, login })
    renderLogin()

    await userEvent.type(screen.getByLabelText('Usuario o correo'), 'ana')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'incorrecta')
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Usuario o contraseña incorrectos.')
  })

  it('incluye un enlace "¿Olvidaste tu contraseña?" hacia /forgot-password', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, login: vi.fn() })
    renderLogin()
    expect(screen.getByRole('link', { name: '¿Olvidaste tu contraseña?' })).toHaveAttribute('href', '/forgot-password')
  })
})
