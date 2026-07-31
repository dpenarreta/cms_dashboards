import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ChartRecommendations from '../components/dashboard-generic/ChartRecommendations'

const RECOMENDACION_KPI = {
  id: 'Saldo::total', tipo_grafica: 'kpi', columna_valor: 'Saldo', columna_categoria: null,
  categorias_unicas: null, datos: { tipo: 'kpi', valor: 1234 },
}

const RECOMENDACION_CHART = {
  id: 'Saldo::Ciudad', tipo_grafica: 'chart', columna_valor: 'Saldo', columna_categoria: 'Ciudad',
  categorias_unicas: 2, columna_serie_sugerida: null,
  datos: { tipo: 'chart', categorias: ['Quito', 'Guayaquil'], valores: [300, 100] },
  datos_multiserie: null,
}

const RECOMENDACION_CHART_CON_SERIE = {
  id: 'Saldo::Ciudad::Causal', tipo_grafica: 'chart', columna_valor: 'Saldo', columna_categoria: 'Ciudad',
  categorias_unicas: 2, columna_serie_sugerida: 'Causal',
  datos: { tipo: 'chart', categorias: ['Quito', 'Guayaquil'], valores: [300, 100] },
  datos_multiserie: {
    tipo: 'multiserie', categorias: ['Quito', 'Guayaquil'],
    series: [{ nombre: 'A', valores: [200, 60] }, { nombre: 'B', valores: [100, 40] }],
  },
}

const RECOMENDACION_DISPERSION = {
  id: 'Saldo::DiasCredito::dispersion', tipo_grafica: 'dispersion', columna_valor: 'Saldo', columna_valor_y: 'Dias credito',
  columna_categoria: null, categorias_unicas: null, columna_serie_sugerida: null,
  datos: { tipo: 'dispersion', puntos: [{ x: 100, y: 10 }, { x: 200, y: 20 }] },
  datos_multiserie: null,
}

function renderComponente(overrides = {}) {
  const props = {
    recomendaciones: [RECOMENDACION_KPI],
    aliases: { Saldo: 'Saldo', Ciudad: 'Ciudad' },
    agregadas: new Set(),
    onAgregar: vi.fn(),
    onVolver: vi.fn(),
    onFinalizar: vi.fn(),
    cargando: false,
    error: null,
    ...overrides,
  }
  const utils = render(<ChartRecommendations {...props} />)
  return { props, ...utils }
}

describe('ChartRecommendations', () => {
  it('todas las recomendaciones muestran un botón de "Vista previa"', () => {
    renderComponente({ recomendaciones: [RECOMENDACION_KPI, RECOMENDACION_CHART] })
    expect(screen.getAllByRole('button', { name: 'Vista previa' })).toHaveLength(2)
  })

  it('"Vista previa" en un KPI muestra el valor calculado', async () => {
    renderComponente()
    expect(screen.queryByText('1.234')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Vista previa' }))
    expect(screen.getByText('1.234')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ocultar vista previa' })).toBeInTheDocument()
  })

  it('"Vista previa" en una gráfica renderiza el GenericBarChart con el título de la recomendación', async () => {
    // recharts no dibuja el SVG en jsdom (depende de ResizeObserver/tamaño real), así que la
    // prueba verifica que el componente de gráfica se montó (su propio título aparece una
    // segunda vez, dentro del contenedor de vista previa) en vez del contenido del SVG.
    renderComponente({ recomendaciones: [RECOMENDACION_CHART] })
    await userEvent.click(screen.getByRole('button', { name: 'Vista previa' }))
    expect(screen.getAllByText('Saldo por Ciudad')).toHaveLength(2)
  })

  it('"Ocultar vista previa" vuelve a colapsarla', async () => {
    renderComponente()
    await userEvent.click(screen.getByRole('button', { name: 'Vista previa' }))
    await userEvent.click(screen.getByRole('button', { name: 'Ocultar vista previa' }))
    expect(screen.queryByText('1.234')).not.toBeInTheDocument()
  })

  it('sin datos calculados, muestra "Vista previa no disponible"', async () => {
    renderComponente({ recomendaciones: [{ ...RECOMENDACION_KPI, datos: null }] })
    await userEvent.click(screen.getByRole('button', { name: 'Vista previa' }))
    expect(screen.getByText('Vista previa no disponible.')).toBeInTheDocument()
  })

  it('previsualizar una tarjeta no afecta a las demás', async () => {
    renderComponente({ recomendaciones: [RECOMENDACION_KPI, RECOMENDACION_CHART] })
    const botones = screen.getAllByRole('button', { name: 'Vista previa' })
    await userEvent.click(botones[0])

    expect(screen.getByText('1.234')).toBeInTheDocument()
    expect(screen.queryByText('Quito')).not.toBeInTheDocument()
  })

  it('"Agregar" sigue funcionando independientemente de la vista previa', async () => {
    const { props } = renderComponente()
    await userEvent.click(screen.getByRole('button', { name: 'Vista previa' }))
    await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))
    expect(props.onAgregar).toHaveBeenCalledWith(RECOMENDACION_KPI, 'kpi')
  })

  describe('selector de tipo de visualización', () => {
    it('un total simple (sin categoría) no muestra selector, solo se puede ver como KPI', () => {
      renderComponente({ recomendaciones: [RECOMENDACION_KPI] })
      expect(screen.queryByLabelText(/Tipo de visualización/)).not.toBeInTheDocument()
    })

    it('una recomendación con categoría muestra el selector con barras horizontales por defecto', () => {
      renderComponente({ recomendaciones: [RECOMENDACION_CHART] })
      const selector = screen.getByLabelText('Tipo de visualización para Saldo por Ciudad')
      expect(selector).toHaveValue('barras_horizontales')
    })

    it('sin columna_serie_sugerida, el selector no ofrece barras agrupadas ni apiladas', () => {
      renderComponente({ recomendaciones: [RECOMENDACION_CHART] })
      const selector = screen.getByLabelText('Tipo de visualización para Saldo por Ciudad')
      const opciones = Array.from(selector.querySelectorAll('option')).map((o) => o.value)
      expect(opciones).not.toContain('barras_agrupadas')
      expect(opciones).not.toContain('barras_apiladas')
    })

    it('con columna_serie_sugerida, el selector sí ofrece barras agrupadas y apiladas', () => {
      renderComponente({ recomendaciones: [RECOMENDACION_CHART_CON_SERIE] })
      const selector = screen.getByLabelText('Tipo de visualización para Saldo por Ciudad')
      const opciones = Array.from(selector.querySelectorAll('option')).map((o) => o.value)
      expect(opciones).toContain('barras_agrupadas')
      expect(opciones).toContain('barras_apiladas')
    })

    it('cambiar el selector a "Pastel" y agregar envía tipo_visualizacion="pastel"', async () => {
      const { props } = renderComponente({ recomendaciones: [RECOMENDACION_CHART] })
      const selector = screen.getByLabelText('Tipo de visualización para Saldo por Ciudad')
      await userEvent.selectOptions(selector, 'pastel')
      await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))
      expect(props.onAgregar).toHaveBeenCalledWith(RECOMENDACION_CHART, 'pastel')
    })

    it('elegir "Barras agrupadas" y ver la vista previa renderiza el gráfico multiserie', async () => {
      renderComponente({ recomendaciones: [RECOMENDACION_CHART_CON_SERIE] })
      const selector = screen.getByLabelText('Tipo de visualización para Saldo por Ciudad')
      await userEvent.selectOptions(selector, 'barras_agrupadas')
      await userEvent.click(screen.getByRole('button', { name: 'Vista previa' }))
      expect(screen.getAllByText('Saldo por Ciudad')).toHaveLength(2)
      expect(screen.queryByText('Vista previa no disponible.')).not.toBeInTheDocument()
    })

    it('con columna_serie_sugerida, el selector también ofrece área apilada', () => {
      renderComponente({ recomendaciones: [RECOMENDACION_CHART_CON_SERIE] })
      const selector = screen.getByLabelText('Tipo de visualización para Saldo por Ciudad')
      const opciones = Array.from(selector.querySelectorAll('option')).map((o) => o.value)
      expect(opciones).toContain('area_apilada')
    })
  })

  describe('recomendación de dispersión', () => {
    it('una recomendación de dispersión no muestra selector, solo se puede ver como Dispersión', () => {
      renderComponente({ recomendaciones: [RECOMENDACION_DISPERSION] })
      expect(screen.queryByLabelText(/Tipo de visualización/)).not.toBeInTheDocument()
      expect(screen.getByText('Dispersión')).toBeInTheDocument()
    })

    it('"Agregar" en una recomendación de dispersión envía tipo_visualizacion="dispersion"', async () => {
      const { props } = renderComponente({ recomendaciones: [RECOMENDACION_DISPERSION] })
      await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))
      expect(props.onAgregar).toHaveBeenCalledWith(RECOMENDACION_DISPERSION, 'dispersion')
    })

    it('"Vista previa" en una dispersión renderiza el GenericScatterChart con el título de la recomendación', async () => {
      renderComponente({ recomendaciones: [RECOMENDACION_DISPERSION] })
      await userEvent.click(screen.getByRole('button', { name: 'Vista previa' }))
      expect(screen.getAllByText('Saldo vs. Dias credito')).toHaveLength(2)
    })
  })
})
