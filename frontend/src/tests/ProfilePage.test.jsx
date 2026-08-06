import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ProfilePage from '../pages/administration/profile/ProfilePage'
import { useAuth } from '../context/AuthContext'
import * as authService from '../services/authService'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../services/authService')

const USUARIO = {
  username: 'ana', email: 'ana@example.com', first_name: 'Ana', last_name: 'Pérez',
  area: 'Cobranzas', avatar_url: null, roles: ['Cobranzas'], is_superuser: false,
}

function renderPagina(usuario = USUARIO, refreshUser = vi.fn().mockResolvedValue(usuario)) {
  useAuth.mockReturnValue({ user: usuario, refreshUser })
  return { ...render(<ProfilePage />), refreshUser }
}

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    if (!URL.createObjectURL) URL.createObjectURL = vi.fn()
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-preview')
  })

  it('muestra la información básica del usuario y sus roles', () => {
    renderPagina()
    expect(screen.getByText('ana')).toBeInTheDocument()
    expect(screen.getByText('ana@example.com')).toBeInTheDocument()
    expect(screen.getByText('Cobranzas')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Ana Pérez')).toBeInTheDocument()
  })

  it('sin avatar_url, muestra la inicial del usuario', () => {
    renderPagina()
    expect(screen.getByText('A')).toBeInTheDocument()
  })

  it('el campo de área se precarga con el área actual', () => {
    renderPagina()
    expect(screen.getByLabelText('Área')).toHaveValue('Cobranzas')
  })

  it('guardar el área llama al servicio y refresca la sesión', async () => {
    const { refreshUser } = renderPagina()
    authService.updateProfile.mockResolvedValue({ ...USUARIO, area: 'Ventas' })

    await userEvent.clear(screen.getByLabelText('Área'))
    await userEvent.type(screen.getByLabelText('Área'), 'Ventas')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar área' }))

    expect(authService.updateProfile).toHaveBeenCalledWith({ area: 'Ventas' })
    await waitFor(() => expect(refreshUser).toHaveBeenCalled())
    expect(await screen.findByText('Área actualizada.')).toBeInTheDocument()
  })

  it('si falla guardar el área, muestra el mensaje de error del backend', async () => {
    renderPagina()
    authService.updateProfile.mockRejectedValue({ response: { data: { mensaje: 'No se pudo.' } } })

    await userEvent.click(screen.getByRole('button', { name: 'Guardar área' }))

    expect(await screen.findByText('No se pudo.')).toBeInTheDocument()
  })

  it('el botón de subir imagen está deshabilitado hasta elegir un archivo', () => {
    renderPagina()
    expect(screen.getByRole('button', { name: 'Subir imagen' })).toBeDisabled()
  })

  it('elegir un archivo y subirlo llama al servicio y refresca la sesión', async () => {
    const { refreshUser } = renderPagina()
    authService.uploadAvatar.mockResolvedValue({ ...USUARIO, avatar_url: 'http://x/avatar.png' })
    const archivo = new File(['contenido'], 'foto.png', { type: 'image/png' })

    const input = screen.getByLabelText('Cambiar avatar')
    await userEvent.upload(input, archivo)
    expect(screen.getByRole('button', { name: 'Subir imagen' })).toBeEnabled()

    await userEvent.click(screen.getByRole('button', { name: 'Subir imagen' }))

    expect(authService.uploadAvatar).toHaveBeenCalledWith(archivo)
    await waitFor(() => expect(refreshUser).toHaveBeenCalled())
  })

  it('si la imagen es rechazada por el backend, muestra el mensaje de error de validación', async () => {
    renderPagina()
    authService.uploadAvatar.mockRejectedValue({ response: { data: { avatar: ['La imagen no puede superar 2 MB.'] } } })
    const archivo = new File(['contenido'], 'foto.png', { type: 'image/png' })

    await userEvent.upload(screen.getByLabelText('Cambiar avatar'), archivo)
    await userEvent.click(screen.getByRole('button', { name: 'Subir imagen' }))

    expect(await screen.findByText('La imagen no puede superar 2 MB.')).toBeInTheDocument()
  })

  it('cambiar la contraseña con confirmación distinta no llama al servicio', async () => {
    renderPagina()
    await userEvent.type(screen.getByLabelText('Contraseña actual'), 'Vieja-123')
    await userEvent.type(screen.getByLabelText('Contraseña nueva'), 'Nueva-12345')
    await userEvent.type(screen.getByLabelText('Confirmar contraseña nueva'), 'Otra-12345')
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))

    expect(screen.getByText('Las contraseñas no coinciden.')).toBeInTheDocument()
    expect(authService.changePassword).not.toHaveBeenCalled()
  })

  it('cambiar la contraseña exitosamente llama al servicio y limpia el formulario', async () => {
    renderPagina()
    authService.changePassword.mockResolvedValue({})
    await userEvent.type(screen.getByLabelText('Contraseña actual'), 'Vieja-123')
    await userEvent.type(screen.getByLabelText('Contraseña nueva'), 'Nueva-12345')
    await userEvent.type(screen.getByLabelText('Confirmar contraseña nueva'), 'Nueva-12345')
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))

    expect(authService.changePassword).toHaveBeenCalledWith({ oldPassword: 'Vieja-123', newPassword: 'Nueva-12345' })
    expect(await screen.findByText('Contraseña actualizada.')).toBeInTheDocument()
    expect(screen.getByLabelText('Contraseña actual')).toHaveValue('')
  })

  it('contraseña actual incorrecta muestra el error del backend', async () => {
    renderPagina()
    authService.changePassword.mockRejectedValue({ response: { data: { mensaje: 'La contraseña actual no es correcta.' } } })
    await userEvent.type(screen.getByLabelText('Contraseña actual'), 'incorrecta')
    await userEvent.type(screen.getByLabelText('Contraseña nueva'), 'Nueva-12345')
    await userEvent.type(screen.getByLabelText('Confirmar contraseña nueva'), 'Nueva-12345')
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar contraseña' }))

    expect(await screen.findByText('La contraseña actual no es correcta.')).toBeInTheDocument()
  })
})
