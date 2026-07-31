import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import DashboardPlaceholderTemplate from '../components/dashboard-generic/DashboardPlaceholderTemplate'

describe('DashboardPlaceholderTemplate', () => {
  it('monta sin errores y muestra el encabezado ilustrativo', () => {
    render(<DashboardPlaceholderTemplate />)
    expect(screen.getByText('Título del Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Subtítulo (Área)')).toBeInTheDocument()
    expect(screen.getByText('Detalle o descripción')).toBeInTheDocument()
  })

  it('muestra las 4 tarjetas KPI con su etiqueta y valor', () => {
    render(<DashboardPlaceholderTemplate />)
    expect(screen.getByText('KPI 1')).toBeInTheDocument()
    expect(screen.getByText('12,458')).toBeInTheDocument()
    expect(screen.getByText('KPI 2')).toBeInTheDocument()
    expect(screen.getByText('$1,245,300')).toBeInTheDocument()
    expect(screen.getByText('KPI 3')).toBeInTheDocument()
    expect(screen.getByText('3,682')).toBeInTheDocument()
    expect(screen.getByText('KPI 4')).toBeInTheDocument()
    expect(screen.getByText('78.6%')).toBeInTheDocument()
  })

  it('muestra los 6 títulos de gráfica y las 3 tablas', () => {
    render(<DashboardPlaceholderTemplate />)
    for (let i = 1; i <= 6; i += 1) {
      expect(screen.getByText(`Gráfico ${i}`)).toBeInTheDocument()
    }
    expect(screen.getByText('Tabla 1')).toBeInTheDocument()
    expect(screen.getByText('Tabla 2')).toBeInTheDocument()
    expect(screen.getByText('Tabla 3')).toBeInTheDocument()
  })

  it('la tabla de productos incluye la fila de total', () => {
    render(<DashboardPlaceholderTemplate />)
    const filaTotal = screen.getByText('Producto A').closest('table')
    expect(filaTotal).toHaveTextContent('Total')
  })
})
