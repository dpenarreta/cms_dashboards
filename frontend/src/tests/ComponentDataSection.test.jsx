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
