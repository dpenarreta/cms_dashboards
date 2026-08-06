import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import HallazgosClaveCard from '../components/dashboard-generic/HallazgosClaveCard'

describe('HallazgosClaveCard', () => {
  it('sin datos suficientes para generar hallazgos, no muestra nada', () => {
    const { container } = render(<HallazgosClaveCard variante="categorico" datos={{ categorias: [], valores: [] }} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('con hallazgos, empieza expandido (el párrafo se ve sin hacer clic)', () => {
    render(<HallazgosClaveCard variante="kpi" datos={{ valor: 100, formato: 'numero' }} />)
    const boton = screen.getByRole('button', { name: /Hallazgos clave/ })
    expect(boton).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/El valor actual es/)).toBeInTheDocument()
  })

  it('un clic en el encabezado contrae el párrafo, y un segundo clic lo vuelve a expandir', async () => {
    const usuario = userEvent.setup()
    render(<HallazgosClaveCard variante="kpi" datos={{ valor: 100, formato: 'numero' }} />)
    const boton = screen.getByRole('button', { name: /Hallazgos clave/ })

    await usuario.click(boton)
    expect(boton).toHaveAttribute('aria-expanded', 'false')

    await usuario.click(boton)
    expect(boton).toHaveAttribute('aria-expanded', 'true')
  })

  it('resalta en negrita los números y nombres importantes del párrafo', () => {
    const { container } = render(
      <HallazgosClaveCard variante="categorico" datos={{ categorias: ['A', 'B'], valores: [10, 20] }} />,
    )
    const negritas = [...container.querySelectorAll('strong')].map((el) => el.textContent)
    expect(negritas).toContain('B')
  })

  it('cambiar los datos (p. ej. tras editar el tipo de gráfico o las columnas) cambia la redacción del párrafo', () => {
    const { container, rerender } = render(<HallazgosClaveCard variante="kpi" datos={{ valor: 100, formato: 'numero' }} />)
    expect(container.querySelector('.hallazgos-clave__texto').textContent).toBe('El valor actual es 100.')

    rerender(<HallazgosClaveCard variante="kpi" datos={{ valor: 500, formato: 'moneda' }} />)
    expect(container.querySelector('.hallazgos-clave__texto').textContent).toMatch(/El valor actual es \$\s*500,00\./)
  })
})
