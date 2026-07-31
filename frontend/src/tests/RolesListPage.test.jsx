import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import RolesListPage from '../pages/administration/roles/RolesListPage'
import * as rolesService from '../services/rolesService'

vi.mock('../services/rolesService')

const ROL = { id: 1, name: 'Cobranzas', permission_codenames: ['dashboard.view', 'dashboard.edit'] }

function renderPagina() {
  return render(<MemoryRouter><RolesListPage /></MemoryRouter>)
}

describe('RolesListPage', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('renderiza los roles con su cantidad de permisos', async () => {
    rolesService.list.mockResolvedValue({ results: [ROL], count: 1, next: null, previous: null })
    renderPagina()
    expect(await screen.findByText('Cobranzas')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('eliminar pide confirmación y llama al servicio', async () => {
    rolesService.list.mockResolvedValue({ results: [ROL], count: 1, next: null, previous: null })
    rolesService.remove.mockResolvedValue({})
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar' }))

    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(rolesService.remove).toHaveBeenCalledWith(1))
  })

  it('si se cancela la confirmación, no elimina', async () => {
    rolesService.list.mockResolvedValue({ results: [ROL], count: 1, next: null, previous: null })
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderPagina()

    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar' }))

    expect(rolesService.remove).not.toHaveBeenCalled()
  })
})
