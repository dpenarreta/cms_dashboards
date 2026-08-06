import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AgregarComponentePersonalModal from '../components/dashboard-editor/AgregarComponentePersonalModal'
import * as carteraService from '../services/carteraService'

vi.mock('../services/carteraService')

const COLUMNAS = [
  { nombre: 'Saldo', tipo: 'numerico', apta_para_valor: true, apta_para_categoria: false },
  { nombre: 'Zona', tipo: 'categorico', apta_para_valor: false, apta_para_categoria: true },
]

const ARCHIVO_DISPONIBLE = {
  disponible: true, carga_id: 'carga-1', nombre_archivo: 'datos.xlsx', total_filas: 100, columnas: COLUMNAS,
}

function renderModal(overrides = {}) {
  const props = {
    show: true,
    onHide: vi.fn(),
    dashboardId: 'finanzas',
    componentesPersonales: [],
    onAgregado: vi.fn(),
    ...overrides,
  }
  return { props, ...render(<AgregarComponentePersonalModal {...props} />) }
}

beforeEach(() => {
  vi.clearAllMocks()
  carteraService.obtenerArchivoActualDashboard.mockResolvedValue(ARCHIVO_DISPONIBLE)
})

describe('AgregarComponentePersonalModal', () => {
  it('sin archivo real aplicado al dashboard, muestra el mensaje correspondiente', async () => {
    carteraService.obtenerArchivoActualDashboard.mockResolvedValue({ disponible: false })
    renderModal()
    expect(await screen.findByText(/todavía no tiene un archivo real cargado/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Agregar' })).not.toBeInTheDocument()
  })

  it('con archivo disponible, muestra el formulario con el tipo "KPI" seleccionado por defecto', async () => {
    renderModal()
    expect(await screen.findByLabelText('Título')).toBeInTheDocument()
    expect(screen.getByLabelText('Tipo de componente')).toHaveValue('kpi')
  })

  it('con tipoInicial, el selector de tipo queda preseleccionado en ese valor', async () => {
    renderModal({ tipoInicial: 'tabla' })
    await screen.findByLabelText('Título')
    expect(screen.getByLabelText('Tipo de componente')).toHaveValue('tabla')
  })

  it('el botón "Agregar" queda deshabilitado sin título', async () => {
    renderModal()
    await screen.findByLabelText('Título')
    expect(screen.getByRole('button', { name: 'Agregar' })).toBeDisabled()
  })

  it('sin componentes previos en la Zona Personal, sugiere 2 columnas de ancho', async () => {
    renderModal({ componentesPersonales: [] })
    expect(await screen.findByLabelText('Ancho')).toHaveValue('2')
  })

  it('con un componente previo de ancho 1 columna (width=12), sugiere repetir 1 columna', async () => {
    renderModal({
      componentesPersonales: [{ component_id: 'a', order: 1, width: 12 }],
    })
    expect(await screen.findByLabelText('Ancho')).toHaveValue('1')
  })

  it('con varios componentes previos, sugiere el ancho del último agregado (mayor order)', async () => {
    renderModal({
      componentesPersonales: [
        { component_id: 'a', order: 1, width: 6 },
        { component_id: 'b', order: 2, width: 3 },
      ],
    })
    expect(await screen.findByLabelText('Ancho')).toHaveValue('4')
  })

  it('elegir tipo "Tabla" muestra el selector de identidad de fila y columnas de valor', async () => {
    renderModal()
    const selectorTipo = await screen.findByLabelText('Tipo de componente')
    await userEvent.selectOptions(selectorTipo, 'tabla')
    expect(screen.getByLabelText(/Identidad de fila/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Columna 1/)).toBeInTheDocument()
  })

  it('confirmar con tipo KPI llama a agregarComponentePersonal con el payload esperado y luego a onAgregado', async () => {
    carteraService.agregarComponentePersonal.mockResolvedValue({})
    const { props } = renderModal()

    await userEvent.type(await screen.findByLabelText('Título'), 'Saldo total')
    await userEvent.selectOptions(screen.getByLabelText(/^Columna de /), 'Saldo')
    await userEvent.selectOptions(screen.getByLabelText('Ancho'), '1')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))

    await waitFor(() => expect(carteraService.agregarComponentePersonal).toHaveBeenCalledWith(
      expect.objectContaining({
        carga_id: 'carga-1', titulo: 'Saldo total', calculo: 'kpi',
        columna_valor: 'Saldo', ancho_columnas: 1,
      }),
    ))
    await waitFor(() => expect(props.onAgregado).toHaveBeenCalledTimes(1))
  })

  it('un error de la API muestra un Alert y no invoca onAgregado', async () => {
    carteraService.agregarComponentePersonal.mockRejectedValue({
      response: { data: { mensaje: 'La gráfica necesita una columna de valor.' } },
    })
    const { props } = renderModal()

    await userEvent.type(await screen.findByLabelText('Título'), 'Sin columna')
    await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))

    expect(await screen.findByText('La gráfica necesita una columna de valor.')).toBeInTheDocument()
    expect(props.onAgregado).not.toHaveBeenCalled()
  })

  it('cancelar invoca onHide', async () => {
    const { props } = renderModal()
    await screen.findByLabelText('Título')
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(props.onHide).toHaveBeenCalledTimes(1)
  })
})
