import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ComponentDataSection from '../components/dashboard-editor/ComponentDataSection'
import * as carteraService from '../services/carteraService'

vi.mock('../services/carteraService')

const COLUMNAS = [
  { nombre: 'Saldo', tipo: 'numerico', apta_para_valor: true, apta_para_categoria: false },
  { nombre: 'Zona', tipo: 'categorico', apta_para_valor: false, apta_para_categoria: true },
]

const ARCHIVO_DISPONIBLE = {
  disponible: true, carga_id: 'carga-1', nombre_archivo: 'datos.xlsx', total_filas: 100, columnas: COLUMNAS,
}

function renderSeccion(overrides = {}) {
  const props = {
    componente: { component_id: 'kpi-1', mapeo: { disponible: true, columna_valor: 'Saldo' } },
    dashboardId: 'finanzas',
    onActualizarComponente: vi.fn(),
    ...overrides,
  }
  return { props, ...render(<ComponentDataSection {...props} />) }
}

beforeEach(() => {
  vi.clearAllMocks()
  carteraService.obtenerArchivoActualDashboard.mockResolvedValue(ARCHIVO_DISPONIBLE)
})

describe('ComponentDataSection', () => {
  it('un componente que no es una posición fija de la plantilla no muestra selectores', async () => {
    renderSeccion({ componente: { component_id: 'grafico-libre-1', mapeo: {} } })
    expect(await screen.findByText('Esta posición no tiene datos configurables desde acá.')).toBeInTheDocument()
  })

  it('sin archivo real aplicado al dashboard, muestra el mensaje correspondiente', async () => {
    carteraService.obtenerArchivoActualDashboard.mockResolvedValue({ disponible: false })
    renderSeccion()
    expect(await screen.findByText(/todavía no tiene un archivo real cargado/)).toBeInTheDocument()
  })

  it('con archivo disponible, precarga los selectores con el mapeo actual del componente', async () => {
    renderSeccion()
    expect(await screen.findByLabelText('Columna de KPI 1')).toHaveValue('Saldo')
    expect(screen.getByLabelText('Tipo de cálculo de KPI 1')).toHaveValue('suma')
  })

  it('cambiar una columna recalcula contra el archivo y actualiza el borrador con el mapeo y el contenido', async () => {
    carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'kpi-1': { titulo: 'KPI 1', valor: 500, formato: 'numero' } } })
    const { props } = renderSeccion()
    const selector = await screen.findByLabelText('Columna de KPI 1')

    await userEvent.selectOptions(selector, 'Zona')

    await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith(
      'carga-1', { 'kpi-1': { disponible: true, columna_valor: 'Zona' } },
    ))
    await waitFor(() => expect(props.onActualizarComponente).toHaveBeenCalledWith('kpi-1', {
      mapeo: { disponible: true, columna_valor: 'Zona' },
      content: { titulo: 'KPI 1', valor: 500, formato: 'numero' },
    }))
  })

  it('cambiar el tipo de cálculo también recalcula (no es un tipo de gráfico)', async () => {
    carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'kpi-1': { titulo: 'KPI 1', valor: 3, formato: 'numero' } } })
    renderSeccion()
    const selector = await screen.findByLabelText('Tipo de cálculo de KPI 1')

    await userEvent.selectOptions(selector, 'conteo_unicos')

    await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith(
      'carga-1', { 'kpi-1': { disponible: true, columna_valor: 'Saldo', tipo_agregacion: 'conteo_unicos' } },
    ))
  })

  it('cambiar el tipo de gráfico no recalcula contra el archivo (los datos no cambian)', async () => {
    const { props } = renderSeccion({
      componente: {
        component_id: 'grafico-1',
        mapeo: { disponible: true, columna_categoria: 'Zona', columna_valor: 'Saldo' },
      },
    })
    const selector = await screen.findByLabelText('Tipo de gráfico de Gráfico 1')

    await userEvent.selectOptions(selector, 'pastel')

    expect(carteraService.previsualizarMapeoPlantilla).not.toHaveBeenCalled()
    expect(props.onActualizarComponente).toHaveBeenCalledWith('grafico-1', {
      mapeo: { disponible: true, columna_categoria: 'Zona', columna_valor: 'Saldo', chart_type: 'pastel' },
      chart_type: 'pastel',
    })
  })

  it('el tipo de cálculo de un KPI no ofrece "Ver valor de celda" (no aplica: un KPI no agrupa filas)', async () => {
    renderSeccion()
    const selector = await screen.findByLabelText('Tipo de cálculo de KPI 1')
    const opciones = Array.from(selector.querySelectorAll('option')).map((o) => o.value)
    expect(opciones).not.toContain('valor_celda')
  })

  it('una posición de 2+ columnas de valor (multivalor/multiserie) también ofrece pastel/dona en el tipo de gráfico', async () => {
    const { props } = renderSeccion({
      componente: {
        component_id: 'grafico-2',
        mapeo: { disponible: true, columna_categoria: 'Zona', columnas_valor: ['Saldo'], chart_type: 'lineas_multiples' },
      },
    })
    const selector = await screen.findByLabelText('Tipo de gráfico de Gráfico 2')
    const opciones = Array.from(selector.querySelectorAll('option')).map((o) => o.value)
    expect(opciones).toEqual(expect.arrayContaining(['pastel', 'dona']))

    await userEvent.selectOptions(selector, 'dona')

    expect(props.onActualizarComponente).toHaveBeenCalledWith('grafico-2', {
      mapeo: { disponible: true, columna_categoria: 'Zona', columnas_valor: ['Saldo'], chart_type: 'dona' },
      chart_type: 'dona',
    })
  })

  it('muestra el selector de columna de filtro, con todas las columnas del archivo', async () => {
    renderSeccion()
    const selectorFiltro = await screen.findByLabelText('Columna de filtro de KPI 1')
    const opciones = Array.from(selectorFiltro.querySelectorAll('option')).map((o) => o.value)
    expect(opciones).toEqual(expect.arrayContaining(['Saldo', 'Zona']))
  })

  describe('etiquetas de los campos según el tipo de gráfico elegido', () => {
    function componenteGrafico1(chartType) {
      return { component_id: 'grafico-1', mapeo: { disponible: true, columna_categoria: 'Zona', columna_valor: 'Saldo', chart_type: chartType } }
    }
    function componenteGrafico3(chartType) {
      return {
        component_id: 'grafico-3',
        mapeo: { disponible: true, columna_categoria: 'Zona', columna_serie: 'Zona', columna_valor: 'Saldo', chart_type: chartType },
      }
    }

    it('barras verticales: "Eje horizontal (categoría)" / "Eje vertical (valor)"', async () => {
      renderSeccion({ componente: componenteGrafico1('barras_verticales') })
      expect(await screen.findByLabelText('Eje horizontal (categoría) de Gráfico 1')).toHaveValue('Zona')
      expect(screen.getByLabelText('Eje vertical (valor) de Gráfico 1')).toHaveValue('Saldo')
    })

    it('barras horizontales: los ejes se invierten en la etiqueta ("Eje vertical" pasa a ser la categoría)', async () => {
      renderSeccion({ componente: componenteGrafico1('barras_horizontales') })
      expect(await screen.findByLabelText('Eje vertical (categoría) de Gráfico 1')).toHaveValue('Zona')
      expect(screen.getByLabelText('Eje horizontal (valor) de Gráfico 1')).toHaveValue('Saldo')
    })

    it('un chart_type ya no seleccionable (p. ej. "lineas", de antes de este cambio) cae a las etiquetas de eje por defecto', async () => {
      // "lineas" ya no está en TIPOS_COMPATIBLES.chart (catálogo cerrado a los 6 tipos vigentes),
      // pero un componente creado antes de este cambio puede seguir teniéndolo guardado —
      // `tipoVisualizacionElegido` cae al tipo por defecto del slot (barras_verticales), así que
      // las etiquetas también caen a las de eje por defecto, no a las circulares.
      renderSeccion({ componente: componenteGrafico1('lineas') })
      expect(await screen.findByLabelText('Eje horizontal (categoría) de Gráfico 1')).toBeInTheDocument()
    })

    it('pastel: "Categoría (una porción por valor)" / "Valor (tamaño de cada porción)", con aviso de leyenda', async () => {
      renderSeccion({ componente: componenteGrafico1('pastel') })
      expect(await screen.findByLabelText('Categoría (una porción por valor) de Gráfico 1')).toHaveValue('Zona')
      expect(screen.getByLabelText('Valor (tamaño de cada porción) de Gráfico 1')).toHaveValue('Saldo')
      expect(screen.getByText(/aparece en la leyenda/)).toBeInTheDocument()
    })

    it('dona: mismas etiquetas circulares que pastel', async () => {
      renderSeccion({ componente: componenteGrafico1('dona') })
      expect(await screen.findByLabelText('Categoría (una porción por valor) de Gráfico 1')).toBeInTheDocument()
      expect(screen.getByText(/aparece en la leyenda/)).toBeInTheDocument()
    })

    it('barras verticales no muestra el aviso de leyenda (solo aplica a pastel/dona)', async () => {
      renderSeccion({ componente: componenteGrafico1('barras_verticales') })
      await screen.findByLabelText('Eje horizontal (categoría) de Gráfico 1')
      expect(screen.queryByText(/aparece en la leyenda/)).not.toBeInTheDocument()
    })

    it('multiserie (Gráfico 3) con líneas múltiples: etiquetas de eje, incluida "Serie"', async () => {
      renderSeccion({ componente: componenteGrafico3('lineas_multiples') })
      expect(await screen.findByLabelText('Eje horizontal (categoría) de Gráfico 3')).toBeInTheDocument()
      expect(screen.getByLabelText('Serie (una barra, línea o capa por cada valor distinto) de Gráfico 3')).toBeInTheDocument()
      expect(screen.getByLabelText('Eje vertical (valor) de Gráfico 3')).toBeInTheDocument()
    })

    it('multiserie (Gráfico 3) con dona: sigue mostrando los 3 campos (Categoría/Serie/Valor), con etiquetas circulares', async () => {
      renderSeccion({ componente: componenteGrafico3('dona') })
      expect(await screen.findByLabelText('Categoría (una porción por valor) de Gráfico 3')).toBeInTheDocument()
      expect(screen.getByLabelText('Serie (se combina en el total de cada porción) de Gráfico 3')).toBeInTheDocument()
      expect(screen.getByLabelText('Valor (tamaño de cada porción) de Gráfico 3')).toBeInTheDocument()
    })
  })

  describe('columnas de valor de un gráfico multivalor (1 "Valor" si es pastel/dona, 2 o 3 "Métrica" si no)', () => {
    function componenteMultivalor(columnasValor, chartType) {
      return {
        component_id: 'grafico-2',
        mapeo: { disponible: true, columna_categoria: 'Zona', columnas_valor: columnasValor, chart_type: chartType },
      }
    }

    it('con un tipo de gráfico no circular, muestra "Métrica 1" y "Métrica 2" (no "Valor")', async () => {
      renderSeccion({ componente: componenteMultivalor(['Saldo'], 'lineas_multiples') })
      expect(await screen.findByLabelText('Métrica 1 de Gráfico 2')).toHaveValue('Saldo')
      expect(screen.getByLabelText('Métrica 2 de Gráfico 2')).toHaveValue('')
      expect(screen.queryByLabelText('Valor (tamaño de cada porción) de Gráfico 2')).not.toBeInTheDocument()
    })

    it('con pastel elegido, muestra un único selector "Valor" (no "Métrica 1"/"Métrica 2")', async () => {
      renderSeccion({ componente: componenteMultivalor(['Saldo', 'Costo'], 'pastel') })
      expect(await screen.findByLabelText('Valor (tamaño de cada porción) de Gráfico 2')).toHaveValue('Saldo')
      expect(screen.queryByLabelText('Métrica 1 de Gráfico 2')).not.toBeInTheDocument()
      expect(screen.queryByLabelText('Métrica 2 de Gráfico 2')).not.toBeInTheDocument()
    })

    it('con dona elegido, también muestra el único selector "Valor"', async () => {
      renderSeccion({ componente: componenteMultivalor(['Saldo'], 'dona') })
      expect(await screen.findByLabelText('Valor (tamaño de cada porción) de Gráfico 2')).toBeInTheDocument()
    })

    it('cambiar de un tipo no circular a pastel colapsa los campos a un único "Valor"', async () => {
      const { rerender } = renderSeccion({ componente: componenteMultivalor(['Saldo', 'Costo'], 'lineas_multiples') })
      await screen.findByLabelText('Métrica 1 de Gráfico 2')

      await userEvent.selectOptions(screen.getByLabelText('Tipo de gráfico de Gráfico 2'), 'pastel')

      rerender(
        <ComponentDataSection
          componente={componenteMultivalor(['Saldo', 'Costo'], 'pastel')} dashboardId="finanzas" onActualizarComponente={vi.fn()}
        />,
      )
      expect(await screen.findByLabelText('Valor (tamaño de cada porción) de Gráfico 2')).toBeInTheDocument()
      expect(screen.queryByLabelText('Métrica 2 de Gráfico 2')).not.toBeInTheDocument()
    })

    it('cambiar de pastel a un tipo no circular expande de nuevo a "Métrica 1"/"Métrica 2"', async () => {
      const { rerender } = renderSeccion({ componente: componenteMultivalor(['Saldo'], 'pastel') })
      await screen.findByLabelText('Valor (tamaño de cada porción) de Gráfico 2')

      rerender(
        <ComponentDataSection
          componente={componenteMultivalor(['Saldo'], 'barras_agrupadas')} dashboardId="finanzas" onActualizarComponente={vi.fn()}
        />,
      )
      expect(await screen.findByLabelText('Métrica 1 de Gráfico 2')).toHaveValue('Saldo')
      expect(screen.getByLabelText('Métrica 2 de Gráfico 2')).toHaveValue('')
    })

    it('"+ Agregar métrica" permite una 3ra columna de valor', async () => {
      carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'grafico-2': { categorias: [], series: [] } } })
      renderSeccion({ componente: componenteMultivalor(['Saldo', 'Costo'], 'lineas_multiples') })
      await screen.findByLabelText('Métrica 1 de Gráfico 2')

      await userEvent.click(screen.getByRole('button', { name: '+ Agregar métrica' }))

      await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith('carga-1', {
        'grafico-2': { disponible: true, columna_categoria: 'Zona', columnas_valor: ['Saldo', 'Costo', null], chart_type: 'lineas_multiples' },
      }))
    })

    it('con 3 métricas, "+ Agregar métrica" ya no aparece y cada fila tiene botón para quitar', async () => {
      carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'grafico-2': { categorias: [], series: [] } } })
      renderSeccion({ componente: componenteMultivalor(['Saldo', 'Costo', 'Zona'], 'lineas_multiples') })
      expect(await screen.findByLabelText('Métrica 3 de Gráfico 2')).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: '+ Agregar métrica' })).not.toBeInTheDocument()

      await userEvent.click(screen.getByLabelText('Quitar métrica 3 de Gráfico 2'))

      await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith('carga-1', {
        'grafico-2': { disponible: true, columna_categoria: 'Zona', columnas_valor: ['Saldo', 'Costo'], chart_type: 'lineas_multiples' },
      }))
    })
  })

  describe('columnas de una tabla (agregar/quitar/reordenar)', () => {
    function componenteTabla(columnasValor) {
      return { component_id: 'tabla-1', mapeo: { disponible: true, columna_id: 'Zona', columnas_valor: columnasValor } }
    }

    it('con una sola columna, "Quitar" queda deshabilitado', async () => {
      renderSeccion({ componente: componenteTabla(['Saldo']) })
      expect(await screen.findByLabelText('Quitar columna 1 de Tabla 1')).toBeDisabled()
    })

    it('"+ Agregar columna" recalcula con una fila vacía extra', async () => {
      carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'tabla-1': { columnas: [], filas: [], total: [] } } })
      renderSeccion({ componente: componenteTabla(['Saldo']) })
      await userEvent.click(await screen.findByRole('button', { name: '+ Agregar columna' }))

      await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith('carga-1', {
        'tabla-1': {
          disponible: true, columna_id: 'Zona',
          columnas_valor: [{ columna: 'Saldo', tipo_agregacion: 'suma' }, { columna: null, tipo_agregacion: 'suma' }],
        },
      }))
    })

    it('"Quitar columna" recalcula sin esa columna', async () => {
      carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'tabla-1': { columnas: [], filas: [], total: [] } } })
      renderSeccion({ componente: componenteTabla(['Saldo', 'Zona']) })
      await userEvent.click(await screen.findByLabelText('Quitar columna 1 de Tabla 1'))

      await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith('carga-1', {
        'tabla-1': { disponible: true, columna_id: 'Zona', columnas_valor: [{ columna: 'Zona', tipo_agregacion: 'suma' }] },
      }))
    })

    it('"Mover abajo" intercambia la columna con la siguiente', async () => {
      carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'tabla-1': { columnas: [], filas: [], total: [] } } })
      renderSeccion({ componente: componenteTabla(['Saldo', 'Zona']) })
      await userEvent.click(await screen.findByLabelText('Mover columna 1 de Tabla 1 abajo'))

      await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith('carga-1', {
        'tabla-1': {
          disponible: true, columna_id: 'Zona',
          columnas_valor: [{ columna: 'Zona', tipo_agregacion: 'suma' }, { columna: 'Saldo', tipo_agregacion: 'suma' }],
        },
      }))
    })

    it('cambiar el tipo de cálculo de una columna de valor recalcula conservando la columna elegida', async () => {
      carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'tabla-1': { columnas: [], filas: [], total: [] } } })
      renderSeccion({ componente: componenteTabla([{ columna: 'Saldo', tipo_agregacion: 'suma' }]) })
      const selector = await screen.findByLabelText('Tipo de cálculo de columna 1 de Tabla 1')

      await userEvent.selectOptions(selector, 'promedio')

      await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith('carga-1', {
        'tabla-1': {
          disponible: true, columna_id: 'Zona',
          columnas_valor: [{ columna: 'Saldo', tipo_agregacion: 'promedio' }],
        },
      }))
    })

    it('el tipo de cálculo de una columna de tabla sí ofrece "Ver valor de celda" y se puede elegir', async () => {
      carteraService.previsualizarMapeoPlantilla.mockResolvedValue({ datos: { 'tabla-1': { columnas: [], filas: [], total: [] } } })
      renderSeccion({ componente: componenteTabla([{ columna: 'Saldo', tipo_agregacion: 'suma' }]) })
      const selector = await screen.findByLabelText('Tipo de cálculo de columna 1 de Tabla 1')
      const opciones = Array.from(selector.querySelectorAll('option')).map((o) => o.value)
      expect(opciones).toContain('valor_celda')

      await userEvent.selectOptions(selector, 'valor_celda')

      await waitFor(() => expect(carteraService.previsualizarMapeoPlantilla).toHaveBeenCalledWith('carga-1', {
        'tabla-1': {
          disponible: true, columna_id: 'Zona',
          columnas_valor: [{ columna: 'Saldo', tipo_agregacion: 'valor_celda' }],
        },
      }))
    })
  })
})
