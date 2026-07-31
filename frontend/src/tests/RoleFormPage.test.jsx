import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RoleFormPage from '../pages/administration/roles/RoleFormPage'
import * as permissionsService from '../services/permissionsService'
import * as rolesService from '../services/rolesService'

vi.mock('../services/rolesService')
vi.mock('../services/permissionsService')

const CATALOGO = { modules: { dashboard: [{ codename: 'dashboard.view', name: 'Ver el dashboard de cartera' }] } }

function renderCrear() {
  return render(
    <MemoryRouter initialEntries={['/admin/roles/new']}>
      <Routes><Route path="/admin/roles/new" element={<RoleFormPage />} /></Routes>
    </MemoryRouter>,
  )
}

function renderEditar() {
  return render(
    <MemoryRouter initialEntries={['/admin/roles/3']}>
      <Routes><Route path="/admin/roles/:id" element={<RoleFormPage />} /></Routes>
    </MemoryRouter>,
  )
}

describe('RoleFormPage — creación', () => {
  beforeEach(() => vi.clearAllMocks())

  it('crea un rol con los permisos marcados', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.create.mockResolvedValue({})
    renderCrear()

    await userEvent.type(await screen.findByLabelText('Nombre del rol'), 'Cobranzas')
    await userEvent.click(screen.getByLabelText('Ver el dashboard de cartera'))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(rolesService.create).toHaveBeenCalledWith({
      name: 'Cobranzas', permission_codenames: ['dashboard.view'],
    }))
  })
})

describe('RoleFormPage — edición', () => {
  beforeEach(() => vi.clearAllMocks())

  it('precarga el nombre y los permisos del rol', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.get.mockResolvedValue({ id: 3, name: 'Cobranzas', permission_codenames: ['dashboard.view'] })
    renderEditar()

    expect(await screen.findByDisplayValue('Cobranzas')).toBeInTheDocument()
    expect(screen.getByLabelText('Ver el dashboard de cartera')).toBeChecked()
  })

  it('al guardar, actualiza el rol', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.get.mockResolvedValue({ id: 3, name: 'Cobranzas', permission_codenames: ['dashboard.view'] })
    rolesService.update.mockResolvedValue({})
    renderEditar()

    await screen.findByDisplayValue('Cobranzas')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(rolesService.update).toHaveBeenCalledWith('3', {
      name: 'Cobranzas', permission_codenames: ['dashboard.view'],
    }))
  })
})
