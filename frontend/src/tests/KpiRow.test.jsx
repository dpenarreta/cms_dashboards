import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import KpiRow from '../components/kpi/KpiRow'
import { DrilldownProvider, useDrilldown } from '../hooks/useDrilldown'

const kpis = {
  fecha_corte: '2026-06-30',
  total_clientes: 928,
  total_documentos: 2281,
  saldo_promedio_por_cliente: 1703.71,
  cartera_total: 1581042.54,
  cartera_vencida: { valor: 302687.53, porcentaje: 19.14 },
  cartera_no_vencida: { valor: 1275683.71, porcentaje: 80.69 },
  sin_fecha_vencimiento: { valor: 2671.3, porcentaje: 0.17, documentos: 1 },
  mayor_120_dias: { valor: 48024.27, porcentaje: 3.04, clientes: 44, documentos: 100 },
  mayor_360_dias: { valor: 33520.96, porcentaje: 2.12, clientes: 16, documentos: 37 },
}

function EstadoDrilldownDebug() {
  const { abierto, titulo, filtrosDrilldown } = useDrilldown()
  return (
    <div data-testid="estado-drilldown">
      {abierto ? `ABIERTO:${titulo}:${JSON.stringify(filtrosDrilldown)}` : 'CERRADO'}
    </div>
  )
}

function renderConProvider(elemento) {
  return render(
    <DrilldownProvider>
      {elemento}
      <EstadoDrilldownDebug />
    </DrilldownProvider>,
  )
}

describe('KpiRow', () => {
  it('no renderiza nada si no hay kpis', () => {
    const { container } = renderConProvider(<KpiRow kpis={null} />)
    expect(container.querySelector('.kpi-card')).not.toBeInTheDocument()
  })

  it('muestra los valores monetarios y de conteo formateados', () => {
    renderConProvider(<KpiRow kpis={kpis} />)

    expect(screen.getByText('Clientes únicos')).toBeInTheDocument()
    expect(screen.getByText('928')).toBeInTheDocument()
    expect(screen.getByText('$ 1.581.042,54')).toBeInTheDocument()
    expect(screen.getByText('$ 302.687,53')).toBeInTheDocument()
    expect(screen.getByText(/corte al 30\/06\/2026/i)).toBeInTheDocument()
  })

  it('al pulsar la tarjeta de cartera vencida abre el detalle con estado_cartera=VENCIDA', async () => {
    renderConProvider(<KpiRow kpis={kpis} />)

    await userEvent.click(screen.getByText('Cartera vencida'))

    expect(screen.getByTestId('estado-drilldown').textContent).toContain('ABIERTO:Cartera vencida')
    expect(screen.getByTestId('estado-drilldown').textContent).toContain('"estado_cartera":"VENCIDA"')
  })

  it('la tarjeta de mora >120 dias envia el filtro de dias_vencidos_min', async () => {
    renderConProvider(<KpiRow kpis={kpis} />)

    await userEvent.click(screen.getByText('Cartera > 120 días'))

    const texto = screen.getByTestId('estado-drilldown').textContent
    expect(texto).toContain('"dias_vencidos_min":121')
  })

  it('la tarjeta es accesible por teclado (rol button y activable con Enter)', async () => {
    renderConProvider(<KpiRow kpis={kpis} />)

    const tarjeta = screen.getByText('Cartera vencida').closest('[role="button"]')
    expect(tarjeta).toHaveAttribute('tabindex', '0')

    tarjeta.focus()
    await userEvent.keyboard('{Enter}')

    expect(screen.getByTestId('estado-drilldown').textContent).toContain('ABIERTO:Cartera vencida')
  })
})
