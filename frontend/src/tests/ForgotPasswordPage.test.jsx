import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ForgotPasswordPage from '../pages/authentication/ForgotPasswordPage'
import * as authService from '../services/authService'

vi.mock('../services/authService')

function renderPagina() {
  return render(<MemoryRouter><ForgotPasswordPage /></MemoryRouter>)
}

const MENSAJE_GENERICO = 'Si el correo está registrado, recibirás un enlace para restablecer tu contraseña.'

describe('ForgotPasswordPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('envía el correo ingresado y muestra el mensaje genérico de éxito', async () => {
    authService.requestPasswordReset.mockResolvedValue({ message: MENSAJE_GENERICO })
    renderPagina()

    await userEvent.type(screen.getByLabelText('Correo electrónico'), 'ana@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace de recuperación' }))

    expect(authService.requestPasswordReset).toHaveBeenCalledWith('ana@example.com')
    expect(await screen.findByText(MENSAJE_GENERICO)).toBeInTheDocument()
  })

  it('muestra el mismo mensaje genérico incluso si el correo no está registrado', async () => {
    // El backend siempre responde 200 con el mismo mensaje — nunca hay una rama de error
    // distinguible para "correo no encontrado" (evita enumeración de usuarios).
    authService.requestPasswordReset.mockResolvedValue({ message: MENSAJE_GENERICO })
    renderPagina()

    await userEvent.type(screen.getByLabelText('Correo electrónico'), 'no-existe@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace de recuperación' }))

    expect(await screen.findByText(MENSAJE_GENERICO)).toBeInTheDocument()
  })

  it('muestra un error si la solicitud falla por completo (red caída)', async () => {
    authService.requestPasswordReset.mockRejectedValue(new Error('red caída'))
    renderPagina()

    await userEvent.type(screen.getByLabelText('Correo electrónico'), 'ana@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace de recuperación' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/no se pudo procesar la solicitud/i)
  })

  it('incluye un enlace para volver al inicio de sesión', () => {
    renderPagina()
    expect(screen.getByRole('link', { name: 'Volver al inicio de sesión' })).toHaveAttribute('href', '/login')
  })
})
