import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AuditListPage from '../pages/administration/audit/AuditListPage'
import * as auditService from '../services/auditService'
import { useAuth } from '../context/AuthContext'

vi.mock('../services/auditService')
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const EVENTO = {
  id: 1, created_at: '2026-07-30T15:24:43.943626Z', domain: 'ROLE_MANAGEMENT', action: 'ROLE_CREATED',
  result: 'SUCCESS', severity: 'INFO', actor_username: 'admin', entity_type: 'role', entity_id: '2',
  entity_name: 'Cobranzas', dashboard_id: '', component_id: '', ip_address: '127.0.0.1', message: '',
}

function renderPagina(permissions = ['auditoria.ver', 'auditoria.ver_detalle', 'auditoria.exportar']) {
  useAuth.mockReturnValue({ user: { permissions } })
  return render(<AuditListPage />)
}

describe('AuditListPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renderiza los eventos devueltos por el backend', async () => {
    auditService.list.mockResolvedValue({ results: [EVENTO], count: 1, next: null, previous: null })
    renderPagina()
    expect(await screen.findByText('ROLE_CREATED')).toBeInTheDocument()
    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText('role: Cobranzas')).toBeInTheDocument()
  })

  it('sin permiso de exportar, no muestra el botón de exportación', async () => {
    auditService.list.mockResolvedValue({ results: [EVENTO], count: 1, next: null, previous: null })
    renderPagina(['auditoria.ver'])
    await screen.findByText('ROLE_CREATED')
    expect(screen.queryByRole('button', { name: /exportar csv/i })).not.toBeInTheDocument()
  })

  it('sin permiso de ver_detalle, no muestra el botón de detalle', async () => {
    auditService.list.mockResolvedValue({ results: [EVENTO], count: 1, next: null, previous: null })
    renderPagina(['auditoria.ver'])
    await screen.findByText('ROLE_CREATED')
    expect(screen.queryByRole('button', { name: 'Detalle' })).not.toBeInTheDocument()
  })

  it('filtrar por dominio dispara una nueva consulta con los filtros aplicados', async () => {
    auditService.list.mockResolvedValue({ results: [], count: 0, next: null, previous: null })
    renderPagina()
    await waitFor(() => expect(auditService.list).toHaveBeenCalledTimes(1))

    await userEvent.selectOptions(screen.getByDisplayValue('Todos los dominios'), 'ROLE_MANAGEMENT')
    await userEvent.click(screen.getByRole('button', { name: 'Filtrar' }))

    await waitFor(() => expect(auditService.list).toHaveBeenLastCalledWith(expect.objectContaining({ domain: 'ROLE_MANAGEMENT', page: 1 })))
  })

  it('el botón "Detalle" abre el modal con los valores anteriores y nuevos', async () => {
    auditService.list.mockResolvedValue({ results: [EVENTO], count: 1, next: null, previous: null })
    auditService.get.mockResolvedValue({
      ...EVENTO, previous_values: {}, new_values: { name: 'Cobranzas' }, metadata: {}, user_agent: '', message: '',
    })
    renderPagina()

    const boton = await screen.findByRole('button', { name: 'Detalle' })
    await userEvent.click(boton)

    expect(await screen.findByText('Detalle del evento de auditoría')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/"name": "Cobranzas"/)).toBeInTheDocument())
  })

  it('muestra un mensaje cuando no hay eventos', async () => {
    auditService.list.mockResolvedValue({ results: [], count: 0, next: null, previous: null })
    renderPagina()
    expect(await screen.findByText(/no hay eventos que coincidan/i)).toBeInTheDocument()
  })

  it('muestra un error si el listado falla', async () => {
    auditService.list.mockRejectedValue(new Error('falló'))
    renderPagina()
    expect(await screen.findByText(/no se pudo cargar el historial de auditoría/i)).toBeInTheDocument()
  })
})
