import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import GenericKpiCard from '../components/dashboard-generic/GenericKpiCard'

describe('GenericKpiCard', () => {
  it('formatea el valor como moneda cuando formato="moneda"', () => {
    const { container } = render(<GenericKpiCard data={{ titulo: 'KPI 2', valor: 1245300, formato: 'moneda' }} />)
    expect(container.querySelector('.kpi-card__value').textContent).toMatch(/\$/)
  })

  it('formatea el valor como porcentaje cuando formato="porcentaje"', () => {
    const { container } = render(<GenericKpiCard data={{ titulo: 'KPI 4', valor: 78.6, formato: 'porcentaje' }} />)
    expect(container.querySelector('.kpi-card__value').textContent).toMatch(/78[,.]6\d?\s?%/)
  })

  it('sin ícono en config, no muestra ningún ícono', () => {
    const { container } = render(<GenericKpiCard data={{ titulo: 'KPI 1', valor: 100, formato: 'numero' }} />)
    expect(container.querySelector('svg')).not.toBeInTheDocument()
  })

  it('con ícono en config, dibuja el círculo de ícono junto al título', () => {
    const { container } = render(
      <GenericKpiCard data={{ titulo: 'KPI 1', valor: 100, formato: 'numero' }} config={{ icono: 'persona' }} />,
    )
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('con tendencia, muestra la línea "↑/↓ x% <texto>" en vez de la descripción', () => {
    render(
      <GenericKpiCard
        data={{ titulo: 'KPI 1', valor: 100, formato: 'numero', descripcion: 'no debería verse', tendencia: { valor: 8.5, texto: 'vs. mes anterior' } }}
      />,
    )
    expect(screen.getByText(/↑ 8.5% vs\. mes anterior/)).toBeInTheDocument()
    expect(screen.queryByText('no debería verse')).not.toBeInTheDocument()
  })

  it('una tendencia negativa se muestra con flecha hacia abajo', () => {
    render(<GenericKpiCard data={{ titulo: 'KPI 1', valor: 100, formato: 'numero', tendencia: { valor: -3.2, texto: 'vs. mes anterior' } }} />)
    expect(screen.getByText(/↓ 3.2% vs\. mes anterior/)).toBeInTheDocument()
  })

  it('sin tendencia, muestra la descripción como el resto de gráficas', () => {
    render(<GenericKpiCard data={{ titulo: 'KPI 1', valor: 100, formato: 'numero', descripcion: 'Suma de "Ventas".' }} />)
    expect(screen.getByText('Suma de "Ventas".')).toBeInTheDocument()
  })
})
