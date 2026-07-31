import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import PermissionsPage from '../pages/administration/permissions/PermissionsPage'
import * as permissionsService from '../services/permissionsService'

vi.mock('../services/permissionsService')

describe('PermissionsPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renderiza el catálogo agrupado por módulo', async () => {
    permissionsService.catalog.mockResolvedValue({
      modules: { usuarios: [{ codename: 'usuarios.ver', name: 'Ver usuarios' }] },
    })
    render(<PermissionsPage />)

    expect(await screen.findByText('usuarios')).toBeInTheDocument()
    expect(screen.getByText('usuarios.ver')).toBeInTheDocument()
    expect(screen.getByText('Ver usuarios')).toBeInTheDocument()
  })

  it('muestra un mensaje de error si falla la consulta', async () => {
    permissionsService.catalog.mockRejectedValue(new Error('red caída'))
    render(<PermissionsPage />)
    expect(await screen.findByText(/no se pudo cargar el catálogo/i)).toBeInTheDocument()
  })
})
