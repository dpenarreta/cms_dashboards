import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ComponentPropertiesPanel from '../components/dashboard-editor/ComponentPropertiesPanel'

function componenteDePrueba(extra = {}) {
  return {
    component_id: 'kpi-cartera-vencida',
    type: 'kpi',
    content: { titulo: 'Cartera vencida', descripcion: '' },
    styles: {},
    width: 2,
    height: 180,
    ...extra,
  }
}

function renderPanel(overrides = {}) {
  const props = {
    componente: componenteDePrueba(),
    onCerrar: vi.fn(),
    onActualizarContenido: vi.fn(),
    onActualizarEstilos: vi.fn(),
    onCambiarAncho: vi.fn(),
    onCambiarAlto: vi.fn(),
    onActualizarConfig: vi.fn(),
    ...overrides,
  }
  return { props, ...render(<ComponentPropertiesPanel {...props} />) }
}

describe('ComponentPropertiesPanel', () => {
  it('no renderiza nada cuando no hay componente seleccionado', () => {
    const { container } = renderPanel({ componente: null })
    expect(container).toBeEmptyDOMElement()
  })

  it('editar el título invoca onActualizarContenido con el component_id y el nuevo título', async () => {
    const { props } = renderPanel()
    const campo = screen.getByLabelText('Título')

    await userEvent.type(campo, '!')

    expect(props.onActualizarContenido).toHaveBeenLastCalledWith('kpi-cartera-vencida', { titulo: 'Cartera vencida!' })
  })

  it('editar la descripción invoca onActualizarContenido', () => {
    const { props } = renderPanel()
    const campo = screen.getByLabelText('Descripción')

    fireEvent.change(campo, { target: { value: 'Detalle' } })

    expect(props.onActualizarContenido).toHaveBeenLastCalledWith('kpi-cartera-vencida', { descripcion: 'Detalle' })
  })

  it('un color hexadecimal válido invoca onActualizarEstilos y no muestra error', async () => {
    const { props } = renderPanel()
    const campo = screen.getByLabelText('Color principal (hexadecimal)')

    await userEvent.type(campo, '#1F4E78')

    expect(props.onActualizarEstilos).toHaveBeenCalledWith('kpi-cartera-vencida', { colorPrincipal: '#1F4E78' })
    expect(screen.queryByText(/color inválido/i)).not.toBeInTheDocument()
  })

  it('un color inválido muestra un error y no invoca onActualizarEstilos', async () => {
    const { props } = renderPanel()
    const campo = screen.getByLabelText('Color principal (hexadecimal)')

    await userEvent.type(campo, 'no-es-un-color')

    expect(screen.getByText(/color inválido/i)).toBeInTheDocument()
    expect(props.onActualizarEstilos).not.toHaveBeenCalled()
  })

  it('"Restablecer colores" limpia todos los campos de color de una vez', async () => {
    const { props } = renderPanel({ componente: componenteDePrueba({ styles: { colorPrincipal: '#112233' } }) })

    await userEvent.click(screen.getByRole('button', { name: 'Restablecer colores' }))

    expect(props.onActualizarEstilos).toHaveBeenCalledWith('kpi-cartera-vencida', expect.objectContaining({
      colorPrincipal: '', colorVencido: '', colorNoVencido: '', colorSinGestion: '', colorTexto: '', colorFondo: '',
    }))
  })

  it('cambiar el ancho invoca onCambiarAncho con el component_id y el número elegido', async () => {
    const { props } = renderPanel()
    await userEvent.selectOptions(screen.getByLabelText('Ancho'), '6')
    expect(props.onCambiarAncho).toHaveBeenCalledWith('kpi-cartera-vencida', 6)
  })

  it('muestra el reordenamiento de filtros solo para el panel de filtros', () => {
    renderPanel({
      componente: componenteDePrueba({
        component_id: 'panel-filtros',
        type: 'filters_panel',
        config: { filtros: [{ id: 'ciudad', label: 'Ciudad', order: 1, width: 2, is_visible: true }] },
      }),
    })
    expect(screen.getByText('Orden de los filtros')).toBeInTheDocument()
  })

  it('no muestra el reordenamiento de filtros para un componente que no es el panel de filtros', () => {
    renderPanel()
    expect(screen.queryByText('Orden de los filtros')).not.toBeInTheDocument()
  })
})
