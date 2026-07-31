import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import DashboardsListPage from '../pages/dashboards/DashboardsListPage'
import * as dashboardLayoutService from '../services/dashboardLayoutService'
import { useAuth } from '../context/AuthContext'

vi.mock('../services/dashboardLayoutService')
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderPagina(permissions = []) {
  useAuth.mockReturnValue({ user: { permissions } })
  return render(<MemoryRouter><DashboardsListPage /></MemoryRouter>)
}

describe('DashboardsListPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('muestra un spinner mientras carga', () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockReturnValue(new Promise(() => {}))
    renderPagina()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renderiza los dashboards autorizados devueltos por el backend, con un botón "Entrar" que enlaza al dashboard', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([
      { dashboard_id: 'cartera', name: 'Dashboard de cartera', area: 'Cartera' },
    ])
    renderPagina()
    expect(await screen.findByText('Dashboard de cartera')).toBeInTheDocument()
    const tarjeta = screen.getByTestId('dashboard-card-cartera')
    expect(within(tarjeta).getByRole('button', { name: 'Entrar' })).toHaveAttribute('href', '/app/dashboards/cartera')
  })

  it('un dashboard que no es "cartera" enlaza a la página genérica por dashboard_id', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([
      { dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' },
    ])
    renderPagina()
    expect(await screen.findByText('Finanzas')).toBeInTheDocument()
    const tarjeta = screen.getByTestId('dashboard-card-finanzas')
    expect(within(tarjeta).getByRole('button', { name: 'Entrar' })).toHaveAttribute('href', '/app/dashboards/finanzas')
  })

  it('muestra un mensaje cuando no hay dashboards autorizados', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([])
    renderPagina()
    expect(await screen.findByText(/no tiene ningún dashboard autorizado/i)).toBeInTheDocument()
  })

  it('muestra un mensaje de error si falla la consulta', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockRejectedValue(new Error('red caída'))
    renderPagina()
    expect(await screen.findByText(/no se pudieron cargar los dashboards/i)).toBeInTheDocument()
  })

  it('sin el permiso dashboard.crear, no muestra el botón de crear dashboard', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([])
    renderPagina([])
    await screen.findByText(/no tiene ningún dashboard autorizado/i)
    expect(screen.queryByRole('button', { name: 'Crear dashboard' })).not.toBeInTheDocument()
  })

  it('con el permiso, crear un dashboard llama al servicio y refresca la lista', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' }])
    dashboardLayoutService.crearDashboard.mockResolvedValue({ dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' })
    renderPagina(['dashboard.crear'])

    await userEvent.click(await screen.findByRole('button', { name: 'Crear dashboard' }))
    await userEvent.type(screen.getByLabelText('Nombre'), 'Finanzas')
    await userEvent.type(screen.getByLabelText('Área'), 'Finanzas')
    await userEvent.click(screen.getByRole('button', { name: 'Crear' }))

    expect(dashboardLayoutService.crearDashboard).toHaveBeenCalledWith({ name: 'Finanzas', area: 'Finanzas', description: '' })
    expect(await screen.findByText('Finanzas')).toBeInTheDocument()
  })

  it('sin los permisos dashboard.editar/dashboard.eliminar, no muestra esos botones en la tarjeta', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([
      { dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' },
    ])
    renderPagina([])
    const tarjeta = await screen.findByTestId('dashboard-card-finanzas')
    expect(within(tarjeta).queryByRole('button', { name: 'Editar' })).not.toBeInTheDocument()
    expect(within(tarjeta).queryByRole('button', { name: 'Eliminar' })).not.toBeInTheDocument()
  })

  it('con el permiso dashboard.editar, editar un dashboard llama al servicio y refresca la lista', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados
      .mockResolvedValueOnce([{ dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' }])
      .mockResolvedValueOnce([{ dashboard_id: 'finanzas', name: 'Finanzas Nacionales', area: 'Finanzas' }])
    dashboardLayoutService.actualizarDashboard.mockResolvedValue({ dashboard_id: 'finanzas', name: 'Finanzas Nacionales', area: 'Finanzas' })
    renderPagina(['dashboard.editar'])

    const tarjeta = await screen.findByTestId('dashboard-card-finanzas')
    await userEvent.click(within(tarjeta).getByRole('button', { name: 'Editar' }))

    const nombreInput = await screen.findByLabelText('Nombre')
    expect(nombreInput).toHaveValue('Finanzas')
    expect(screen.getByLabelText('Área')).toHaveValue('Finanzas y Contabilidad')

    await userEvent.clear(nombreInput)
    await userEvent.type(nombreInput, 'Finanzas Nacionales')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(dashboardLayoutService.actualizarDashboard).toHaveBeenCalledWith('finanzas', { name: 'Finanzas Nacionales', area: 'Finanzas y Contabilidad' })
    expect(await screen.findByText('Finanzas Nacionales')).toBeInTheDocument()
  })

  it('con el permiso dashboard.eliminar, el botón Eliminar exige escribir el nombre exacto y muestra ese nombre en un <span>', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([
      { dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' },
    ])
    renderPagina(['dashboard.eliminar'])

    const tarjeta = await screen.findByTestId('dashboard-card-finanzas')
    await userEvent.click(within(tarjeta).getByRole('button', { name: 'Eliminar' }))

    const dialogo = await screen.findByRole('dialog')
    const spanNombre = within(dialogo).getByText('Finanzas', { selector: 'span' })
    expect(spanNombre).toBeInTheDocument()

    const botonEliminar = within(dialogo).getByRole('button', { name: 'Eliminar' })
    expect(botonEliminar).toBeDisabled()

    await userEvent.type(screen.getByLabelText('Confirmar nombre del dashboard'), 'nombre incorrecto')
    expect(botonEliminar).toBeDisabled()
  })

  it('escribiendo el nombre exacto, eliminar llama al servicio con la confirmación y refresca la lista', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados
      .mockResolvedValueOnce([{ dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' }])
      .mockResolvedValueOnce([])
    dashboardLayoutService.eliminarDashboard.mockResolvedValue({})
    renderPagina(['dashboard.eliminar'])

    const tarjeta = await screen.findByTestId('dashboard-card-finanzas')
    await userEvent.click(within(tarjeta).getByRole('button', { name: 'Eliminar' }))

    const dialogo = await screen.findByRole('dialog')
    await userEvent.type(within(dialogo).getByLabelText('Confirmar nombre del dashboard'), 'Finanzas')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Eliminar' }))

    expect(dashboardLayoutService.eliminarDashboard).toHaveBeenCalledWith('finanzas', 'Finanzas')
    expect(await screen.findByText(/no tiene ningún dashboard autorizado/i)).toBeInTheDocument()
  })

  it('si la eliminación falla, muestra el mensaje de error del backend', async () => {
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([
      { dashboard_id: 'finanzas', name: 'Finanzas', area: '' },
    ])
    dashboardLayoutService.eliminarDashboard.mockRejectedValue({ response: { data: { mensaje: 'El nombre ingresado no coincide.' } } })
    renderPagina(['dashboard.eliminar'])

    const tarjeta = await screen.findByTestId('dashboard-card-finanzas')
    await userEvent.click(within(tarjeta).getByRole('button', { name: 'Eliminar' }))

    const dialogo = await screen.findByRole('dialog')
    await userEvent.type(within(dialogo).getByLabelText('Confirmar nombre del dashboard'), 'Finanzas')
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Eliminar' }))

    expect(await screen.findByText('El nombre ingresado no coincide.')).toBeInTheDocument()
  })
})
