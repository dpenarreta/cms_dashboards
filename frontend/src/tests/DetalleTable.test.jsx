import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DetalleTable from '../components/table/DetalleTable'
import * as carteraService from '../services/carteraService'

vi.mock('../services/carteraService', () => ({
  obtenerDetalle: vi.fn(),
  urlExportar: vi.fn(() => '#'),
}))

describe('DetalleTable', () => {
  it('muestra el estado de carga mientras llega la respuesta', () => {
    carteraService.obtenerDetalle.mockReturnValue(new Promise(() => {})) // nunca se resuelve
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" />)
    expect(screen.getByText(/cargando/i)).toBeInTheDocument()
  })

  it('muestra un estado sin resultados cuando el backend no devuelve filas', async () => {
    carteraService.obtenerDetalle.mockResolvedValue({ count: 0, results: [] })
    render(<DetalleTable cargaId="c1" filtros={{ ciudad: 'CIUDAD_INEXISTENTE' }} fechaCorte="2026-06-30" />)

    expect(await screen.findByText(/no hay registros que cumplan los filtros/i)).toBeInTheDocument()
  })

  it('muestra un estado de error cuando la consulta falla (por ejemplo, 403)', async () => {
    carteraService.obtenerDetalle.mockRejectedValue({ response: { status: 403, data: { mensaje: 'No autorizado.' } } })
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" />)

    expect(await screen.findByText('No autorizado.')).toBeInTheDocument()
  })

  it('renderiza las filas devueltas por el backend', async () => {
    carteraService.obtenerDetalle.mockResolvedValue({
      count: 1,
      results: [{
        cliente: 'ACME', ruc_cliente: '123', numero_documento: 'DOC-1', fecha_emision: '2026-05-01',
        fecha_vencimiento: '2026-06-01', dias_vencidos: 10, saldo: 500, ciudad: 'QUITO',
        recuperador: 'R01', causal: 'GESTIONANDO', estado_calculado: 'VENCIDA', rango_mora: '0-30 DÍAS',
      }],
    })
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" />)

    await waitFor(() => expect(screen.getByText('ACME')).toBeInTheDocument())
  })

  it('el buscador está contraído por defecto y se expande/contrae con el botón', async () => {
    carteraService.obtenerDetalle.mockResolvedValue({ count: 0, results: [] })
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" />)

    expect(screen.queryByPlaceholderText(/buscar por cliente/i)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /mostrar buscador/i }))
    const input = screen.getByPlaceholderText(/buscar por cliente/i)
    expect(input).toBeInTheDocument()

    await userEvent.type(input, 'ACME')
    expect(input).toHaveValue('ACME')

    await userEvent.click(screen.getByRole('button', { name: /contraer buscador/i }))
    expect(screen.queryByPlaceholderText(/buscar por cliente/i)).not.toBeInTheDocument()
  })

  it('usa el page_size devuelto por el backend para calcular el total de páginas', async () => {
    carteraService.obtenerDetalle.mockResolvedValue({ count: 48, page_size: 25, results: [] })
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" />)

    expect(await screen.findByText('Página 1 de 2')).toBeInTheDocument()
  })

  it('inicializa con el defaultPageSize recibido en override.config', async () => {
    carteraService.obtenerDetalle.mockResolvedValue({ count: 0, page_size: 25, results: [] })
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" override={{ config: { defaultPageSize: 25 } }} />)

    await waitFor(() => expect(carteraService.obtenerDetalle).toHaveBeenCalledWith('c1', expect.objectContaining({ page_size: 25 })))
  })

  it('cambiar el tamaño de página vuelve a consultar desde la página 1 con el nuevo tamaño', async () => {
    carteraService.obtenerDetalle.mockResolvedValue({ count: 100, page_size: 10, results: [] })
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" />)

    await waitFor(() => expect(carteraService.obtenerDetalle).toHaveBeenCalledWith('c1', expect.objectContaining({ page: 1, page_size: 10 })))

    await userEvent.selectOptions(screen.getByLabelText('Registros por página'), '50')

    await waitFor(() => expect(carteraService.obtenerDetalle).toHaveBeenCalledWith('c1', expect.objectContaining({ page: 1, page_size: 50 })))
  })

  it('mantiene los botones de primera y última página', async () => {
    carteraService.obtenerDetalle.mockResolvedValue({ count: 100, page_size: 10, results: [] })
    render(<DetalleTable cargaId="c1" filtros={{}} fechaCorte="2026-06-30" />)

    expect(await screen.findByRole('button', { name: 'Primera página' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Última página' })).toBeInTheDocument()
  })
})
