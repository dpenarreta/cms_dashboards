import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import FiltersPanel from '../components/filters/FiltersPanel'

const filtrosVacios = {
  cliente: '', ciudad: '', zona: '', sucursal: '', recuperador: '', causal: '',
  estado_cartera: '', rango_mora: '', producto: '', articulo: '', tipo_venta: '', estado_cliente: '',
  fecha_vencimiento_desde: '', fecha_vencimiento_hasta: '', fecha_emision_desde: '', fecha_emision_hasta: '',
}

function renderPanel(overrides = {}) {
  return render(
    <FiltersPanel
      filtros={filtrosVacios}
      onCambiarFiltro={vi.fn()}
      onAplicar={vi.fn()}
      onLimpiar={vi.fn()}
      recuperadores={[]}
      causales={null}
      resumenFiltrado={null}
      {...overrides}
    />,
  )
}

describe('FiltersPanel', () => {
  it('muestra los cuatro campos de rango de fecha (vencimiento y emisión)', () => {
    renderPanel()
    expect(screen.getByText('Vencimiento desde')).toBeInTheDocument()
    expect(screen.getByText('Vencimiento hasta')).toBeInTheDocument()
    expect(screen.getByText('Emisión desde')).toBeInTheDocument()
    expect(screen.getByText('Emisión hasta')).toBeInTheDocument()
  })

  it('llama a onCambiarFiltro con el campo y valor correctos al cambiar una fecha', async () => {
    const onCambiarFiltro = vi.fn()
    renderPanel({ onCambiarFiltro })

    const campo = screen.getByText('Vencimiento desde').parentElement.querySelector('input[type="date"]')
    await userEvent.type(campo, '2026-05-01')

    expect(onCambiarFiltro).toHaveBeenCalledWith('fecha_vencimiento_desde', expect.stringContaining('2026'))
  })

  it('la sección de filtros está expandida por defecto y el botón alterna a "Expandir"/"Contraer"', async () => {
    renderPanel()

    expect(screen.getByRole('button', { name: /contraer/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /contraer/i }))
    expect(screen.getByRole('button', { name: /expandir/i })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /expandir/i }))
    expect(screen.getByRole('button', { name: /contraer/i })).toBeInTheDocument()
  })

  it('muestra el resumen de registros filtrados aunque la sección esté contraída', async () => {
    renderPanel({ resumenFiltrado: { count: 5, saldo_filtrado: 100.5, porcentaje_sobre_cartera_total: 10 } })

    await userEvent.click(screen.getByRole('button', { name: /contraer/i }))

    expect(screen.getByText(/5 registros visibles/)).toBeInTheDocument()
  })
})
