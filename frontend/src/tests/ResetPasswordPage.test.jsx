import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ResetPasswordPage from '../pages/authentication/ResetPasswordPage'
import * as authService from '../services/authService'

vi.mock('../services/authService')

function renderPagina(token = 'token-valido') {
  return render(
    <MemoryRouter initialEntries={[`/reset-password?token=${token}`]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/login" element={<div>pagina-login</div>} />
        <Route path="/forgot-password" element={<div>pagina-forgot-password</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ResetPasswordPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('valida el token al cargar y muestra el formulario si es válido', async () => {
    authService.validatePasswordResetToken.mockResolvedValue({ valid: true })
    renderPagina()

    expect(await screen.findByLabelText('Nueva contraseña')).toBeInTheDocument()
    expect(authService.validatePasswordResetToken).toHaveBeenCalledWith('token-valido')
  })

  it('si el token es inválido o expiró, muestra un error y un enlace para solicitar uno nuevo', async () => {
    authService.validatePasswordResetToken.mockRejectedValue(new Error('token inválido'))
    renderPagina('token-expirado')

    expect(await screen.findByRole('alert')).toHaveTextContent(/no es válido o ya expiró/i)
    expect(screen.getByRole('link', { name: 'Solicitar un nuevo enlace' })).toHaveAttribute('href', '/forgot-password')
  })

  it('sin token en la URL, no intenta validar y muestra el estado inválido', async () => {
    renderPagina('')
    expect(await screen.findByRole('alert')).toHaveTextContent(/no es válido o ya expiró/i)
    expect(authService.validatePasswordResetToken).not.toHaveBeenCalled()
  })

  it('marca error si las contraseñas no coinciden y no envía la solicitud', async () => {
    authService.validatePasswordResetToken.mockResolvedValue({ valid: true })
    renderPagina()
    await screen.findByLabelText('Nueva contraseña')

    await userEvent.type(screen.getByLabelText('Nueva contraseña'), 'Clave-Nueva-789')
    await userEvent.type(screen.getByLabelText('Confirmar contraseña'), 'Otra-Clave-000')
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer contraseña' }))

    expect(screen.getByText('Las contraseñas no coinciden.')).toBeInTheDocument()
    expect(authService.confirmPasswordReset).not.toHaveBeenCalled()
  })

  it('al confirmar exitosamente, muestra confirmación y redirige al login', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    authService.validatePasswordResetToken.mockResolvedValue({ valid: true })
    authService.confirmPasswordReset.mockResolvedValue({ message: 'ok' })
    renderPagina()
    await screen.findByLabelText('Nueva contraseña')

    await userEvent.type(screen.getByLabelText('Nueva contraseña'), 'Clave-Nueva-789')
    await userEvent.type(screen.getByLabelText('Confirmar contraseña'), 'Clave-Nueva-789')
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer contraseña' }))

    expect(await screen.findByText(/actualizada correctamente/i)).toBeInTheDocument()
    expect(authService.confirmPasswordReset).toHaveBeenCalledWith({
      token: 'token-valido', newPassword: 'Clave-Nueva-789', confirmPassword: 'Clave-Nueva-789',
    })

    vi.advanceTimersByTime(2500)
    await waitFor(() => expect(screen.getByText('pagina-login')).toBeInTheDocument())
    vi.useRealTimers()
  })

  it('muestra un error del servidor si la confirmación falla (token expirado entre validar y confirmar)', async () => {
    authService.validatePasswordResetToken.mockResolvedValue({ valid: true })
    authService.confirmPasswordReset.mockRejectedValue({ response: { data: { mensaje: 'El enlace de recuperación expiró. Solicita uno nuevo.' } } })
    renderPagina()
    await screen.findByLabelText('Nueva contraseña')

    await userEvent.type(screen.getByLabelText('Nueva contraseña'), 'Clave-Nueva-789')
    await userEvent.type(screen.getByLabelText('Confirmar contraseña'), 'Clave-Nueva-789')
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer contraseña' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('El enlace de recuperación expiró. Solicita uno nuevo.')
  })
})
