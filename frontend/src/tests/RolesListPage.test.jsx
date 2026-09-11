import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import RolesListPage from '../pages/administration/roles/RolesListPage'
import * as rolesService from '../services/rolesService'
import { useAuth } from '../context/AuthContext'

vi.mock('../services/rolesService')
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const ROL = { id: 1, name: 'Cobranzas', permission_codenames: ['dashboard.view', 'dashboard.edit'] }

function renderPagina() {
  return render(<MemoryRouter><RolesListPage /></MemoryRouter>)
}

describe('RolesListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { permissions: [] } })
  })
  afterEach(() => vi.restoreAllMocks())

  it('renderiza los roles con su cantidad de permisos', async () => {
    rolesService.list.mockResolvedValue({ results: [ROL], count: 1, next: null, previous: null })
    renderPagina()
    expect(await screen.findByText('Cobranzas')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('eliminar pide confirmación en un modal y llama al servicio al confirmar', async () => {
    rolesService.list.mockResolvedValue({ results: [ROL], count: 1, next: null, previous: null })
    rolesService.remove.mockResolvedValue({})
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar' }))

    // El clic solo abre el modal: todavía no se llamó al servicio.
    expect(rolesService.remove).not.toHaveBeenCalled()
    // `Modal.Title` de react-bootstrap renderiza un div, no un heading — se consulta por texto.
    expect(screen.getByText('Eliminar rol')).toBeInTheDocument()

    // El botón de confirmar del modal es el segundo "Eliminar" del documento (el primero es el
    // de la fila de la tabla, que sigue montado detrás).
    const botonesEliminar = screen.getAllByRole('button', { name: 'Eliminar' })
    await userEvent.click(botonesEliminar[botonesEliminar.length - 1])

    await waitFor(() => expect(rolesService.remove).toHaveBeenCalledWith(1))
  })

  it('si se cancela el modal, no elimina', async () => {
    rolesService.list.mockResolvedValue({ results: [ROL], count: 1, next: null, previous: null })
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(rolesService.remove).not.toHaveBeenCalled()
  })

  it('no usa el diálogo nativo del navegador para confirmar', async () => {
    // `window.confirm` no es accesible ni testeable y la regla del repo lo prohíbe para acciones
    // destructivas (`.claude/rules/dashboards.md`).
    const confirmSpy = vi.spyOn(window, 'confirm')
    rolesService.list.mockResolvedValue({ results: [ROL], count: 1, next: null, previous: null })
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar' }))

    expect(confirmSpy).not.toHaveBeenCalled()
  })

  it('con permiso para ver usuarios además de roles, muestra la pestaña "Usuarios" para moverse entre ambas listas', async () => {
    useAuth.mockReturnValue({ user: { permissions: ['usuarios.ver', 'roles.ver'] } })
    rolesService.list.mockResolvedValue({ results: [], count: 0, next: null, previous: null })
    renderPagina()
    expect(await screen.findByRole('link', { name: 'Usuarios' })).toHaveAttribute('href', '/admin/users')
  })
})
