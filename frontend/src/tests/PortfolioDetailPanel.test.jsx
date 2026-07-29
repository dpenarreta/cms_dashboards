import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PortfolioDetailPanel from '../components/drilldown/PortfolioDetailPanel'
import { DrilldownProvider, useDrilldown } from '../hooks/useDrilldown'

vi.mock('../services/carteraService', () => ({
  obtenerDetalle: vi.fn().mockResolvedValue({
    count: 1,
    results: [{
      cliente: 'ACME', ruc_cliente: '123', numero_documento: 'DOC-1', fecha_emision: '2026-05-01',
      fecha_vencimiento: '2026-06-01', dias_vencidos: 10, saldo: 500, ciudad: 'QUITO',
      recuperador: 'R01', causal: 'GESTIONANDO', estado_calculado: 'VENCIDA', rango_mora: '0-30 DÍAS',
    }],
  }),
  urlExportar: vi.fn(() => '#'),
}))

function BotonAbrir() {
  const { abrirDetalle } = useDrilldown()
  return (
    <button
      type="button"
      onClick={() => abrirDetalle({
        origen: 'test', titulo: 'Cartera vencida de QUITO', filtros: { estado_cartera: 'VENCIDA', ciudad: 'QUITO' },
      })}
    >
      Abrir
    </button>
  )
}

function renderPanel(filtrosGlobales = { recuperador: 'R01' }) {
  return render(
    <DrilldownProvider>
      <BotonAbrir />
      <PortfolioDetailPanel cargaId="abc-123" fechaCorte="2026-06-30" filtrosGlobales={filtrosGlobales} />
    </DrilldownProvider>,
  )
}

describe('PortfolioDetailPanel', () => {
  it('no muestra contenido cuando no hay una selección de drill-down activa', () => {
    renderPanel()
    expect(screen.queryByText('Cartera vencida de QUITO')).not.toBeInTheDocument()
  })

  it('abre el panel con el título y los filtros de la selección, conservando los filtros globales', async () => {
    renderPanel({ recuperador: 'R01' })

    await userEvent.click(screen.getByText('Abrir'))

    expect(await screen.findByText('Cartera vencida de QUITO')).toBeInTheDocument()
    expect(screen.getByText(/Estado de cartera: VENCIDA/)).toBeInTheDocument()
    expect(screen.getByText(/Ciudad: QUITO/)).toBeInTheDocument()
    expect(screen.getByText(/Recuperador: R01/)).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('ACME')).toBeInTheDocument())
  })

  it('quitar un filtro de drill-down no elimina los filtros globales', async () => {
    renderPanel({ recuperador: 'R01' })
    await userEvent.click(screen.getByText('Abrir'))
    await screen.findByText('Cartera vencida de QUITO')

    const quitarCiudad = screen.getByLabelText('Quitar filtro Ciudad')
    await userEvent.click(quitarCiudad)

    expect(screen.queryByText(/Ciudad: QUITO/)).not.toBeInTheDocument()
    expect(screen.getByText(/Recuperador: R01/)).toBeInTheDocument()
    expect(screen.getByText(/Estado de cartera: VENCIDA/)).toBeInTheDocument()
  })

  it('cerrar el panel oculta el detalle sin lanzar errores', async () => {
    renderPanel()
    await userEvent.click(screen.getByText('Abrir'))
    await screen.findByText('Cartera vencida de QUITO')

    await userEvent.click(screen.getByText('Volver al dashboard'))

    await waitFor(() => expect(screen.queryByText('Cartera vencida de QUITO')).not.toBeInTheDocument())
  })
})
