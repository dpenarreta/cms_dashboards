import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import UsersListPage from '../pages/administration/users/UsersListPage'
import * as usersService from '../services/usersService'
import { useAuth } from '../context/AuthContext'

vi.mock('../services/usersService')
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const USUARIO_ACTIVO = {
  id: 1, username: 'ana', email: 'ana@example.com', first_name: 'Ana', last_name: 'Pérez',
  status: 'active', is_superuser: false, roles: ['Cobranzas'],
}

function renderPagina() {
  return render(<MemoryRouter><UsersListPage /></MemoryRouter>)
}

describe('UsersListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { permissions: [] } })
  })

  it('renderiza los usuarios devueltos por el backend', async () => {
    usersService.list.mockResolvedValue({ results: [USUARIO_ACTIVO], count: 1, next: null, previous: null })
    renderPagina()
    expect(await screen.findByText('ana')).toBeInTheDocument()
    expect(screen.getByText('ana@example.com')).toBeInTheDocument()
    expect(screen.getByText('Cobranzas')).toBeInTheDocument()
  })

  it('un usuario activo muestra el botón "Deshabilitar", que llama al servicio', async () => {
    usersService.list.mockResolvedValue({ results: [USUARIO_ACTIVO], count: 1, next: null, previous: null })
    usersService.disable.mockResolvedValue({ ...USUARIO_ACTIVO, status: 'disabled' })
    renderPagina()

    const boton = await screen.findByRole('button', { name: 'Deshabilitar' })
    await userEvent.click(boton)

    expect(usersService.disable).toHaveBeenCalledWith(1)
    await waitFor(() => expect(usersService.list).toHaveBeenCalledTimes(2))
  })

  it('buscar dispara una nueva consulta con el término ingresado', async () => {
    usersService.list.mockResolvedValue({ results: [], count: 0, next: null, previous: null })
    renderPagina()
    await waitFor(() => expect(usersService.list).toHaveBeenCalledTimes(1))

    await userEvent.type(screen.getByPlaceholderText(/buscar por usuario/i), 'ana')

    await waitFor(() => expect(usersService.list).toHaveBeenLastCalledWith(expect.objectContaining({ q: 'ana' })))
  })

  it('muestra un mensaje cuando no hay usuarios', async () => {
    usersService.list.mockResolvedValue({ results: [], count: 0, next: null, previous: null })
    renderPagina()
    expect(await screen.findByText(/no hay usuarios que coincidan/i)).toBeInTheDocument()
  })
})

describe('UsersListPage — restablecer contraseña', () => {
  beforeEach(() => vi.clearAllMocks())

  it('sin el permiso "usuarios.restablecer_password", no muestra el botón', async () => {
    useAuth.mockReturnValue({ user: { permissions: [] } })
    usersService.list.mockResolvedValue({ results: [USUARIO_ACTIVO], count: 1, next: null, previous: null })
    renderPagina()
    await screen.findByText('ana')
    expect(screen.queryByRole('button', { name: 'Restablecer contraseña' })).not.toBeInTheDocument()
  })

  it('con el permiso, confirmar el restablecimiento llama al servicio y muestra la contraseña generada', async () => {
    useAuth.mockReturnValue({ user: { permissions: ['usuarios.restablecer_password'] } })
    usersService.list.mockResolvedValue({ results: [USUARIO_ACTIVO], count: 1, next: null, previous: null })
    usersService.resetPassword.mockResolvedValue({ temporary_password: 'Abc123XyZ9' })
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Restablecer contraseña' }))
    expect(await screen.findByText(/se generará una nueva contraseña temporal/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Restablecer' }))

    expect(usersService.resetPassword).toHaveBeenCalledWith(1)
    expect(await screen.findByDisplayValue('Abc123XyZ9')).toBeInTheDocument()
    await waitFor(() => expect(usersService.list).toHaveBeenCalledTimes(2))
  })

  it('cancelar la confirmación no llama al servicio', async () => {
    useAuth.mockReturnValue({ user: { permissions: ['usuarios.restablecer_password'] } })
    usersService.list.mockResolvedValue({ results: [USUARIO_ACTIVO], count: 1, next: null, previous: null })
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Restablecer contraseña' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(usersService.resetPassword).not.toHaveBeenCalled()
  })

  it('si el servicio falla, muestra un mensaje de error', async () => {
    useAuth.mockReturnValue({ user: { permissions: ['usuarios.restablecer_password'] } })
    usersService.list.mockResolvedValue({ results: [USUARIO_ACTIVO], count: 1, next: null, previous: null })
    usersService.resetPassword.mockRejectedValue(new Error('falló'))
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Restablecer contraseña' }))
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer' }))

    expect(await screen.findByText('No se pudo restablecer la contraseña del usuario.')).toBeInTheDocument()
  })
})
