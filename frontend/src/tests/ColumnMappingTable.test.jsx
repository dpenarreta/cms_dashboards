import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ColumnMappingTable from '../components/mapping/ColumnMappingTable'

const archivoInfo = {
  nombreArchivo: 'cartera.xlsx',
  tamanoBytes: 12345,
  totalFilas: 100,
  hojasDisponibles: ['Hoja1'],
  hojaSeleccionada: 'Hoja1',
}

function mapeoSugeridoBase() {
  return {
    obligatorios: [
      { campo: 'cliente', etiqueta: 'Cliente', columna_detectada: 'Cliente', estado: 'ENCONTRADA' },
      { campo: 'causal', etiqueta: 'Causal', columna_detectada: null, estado: 'NO_ENCONTRADA' },
    ],
    opcionales: [
      { campo: 'zona', etiqueta: 'Zona', columna_detectada: 'Zona', estado: 'ENCONTRADA' },
    ],
    columnas_disponibles: ['Cliente', 'Causal', 'Zona'],
  }
}

describe('ColumnMappingTable', () => {
  it('deshabilita Procesar dashboard mientras falte un campo obligatorio', () => {
    render(
      <ColumnMappingTable
        archivoInfo={archivoInfo}
        mapeoSugerido={mapeoSugeridoBase()}
        mapeoConfirmado={{ cliente: 'Cliente', causal: '', zona: 'Zona' }}
        onActualizarMapeo={vi.fn()}
        previewFilas={[]}
        onProcesar={vi.fn()}
        onLimpiar={vi.fn()}
        onCambiarHoja={vi.fn()}
        cargando={false}
        error={null}
        fechaCorte=""
        onCambiarFechaCorte={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /procesar dashboard/i })).toBeDisabled()
    expect(screen.getByText(/faltan columnas obligatorias/i)).toBeInTheDocument()
  })

  it('habilita Procesar dashboard cuando todos los obligatorios estan mapeados', () => {
    render(
      <ColumnMappingTable
        archivoInfo={archivoInfo}
        mapeoSugerido={mapeoSugeridoBase()}
        mapeoConfirmado={{ cliente: 'Cliente', causal: 'Causal', zona: 'Zona' }}
        onActualizarMapeo={vi.fn()}
        previewFilas={[]}
        onProcesar={vi.fn()}
        onLimpiar={vi.fn()}
        onCambiarHoja={vi.fn()}
        cargando={false}
        error={null}
        fechaCorte=""
        onCambiarFechaCorte={vi.fn()}
      />,
    )

    expect(screen.getByRole('button', { name: /procesar dashboard/i })).toBeEnabled()
  })

  it('llama a onActualizarMapeo al cambiar el dropdown de un campo', async () => {
    const onActualizarMapeo = vi.fn()
    render(
      <ColumnMappingTable
        archivoInfo={archivoInfo}
        mapeoSugerido={mapeoSugeridoBase()}
        mapeoConfirmado={{ cliente: 'Cliente', causal: '', zona: 'Zona' }}
        onActualizarMapeo={onActualizarMapeo}
        previewFilas={[]}
        onProcesar={vi.fn()}
        onLimpiar={vi.fn()}
        onCambiarHoja={vi.fn()}
        cargando={false}
        error={null}
        fechaCorte=""
        onCambiarFechaCorte={vi.fn()}
      />,
    )

    const selectCausal = screen.getByLabelText(/columna para causal/i)
    await userEvent.selectOptions(selectCausal, 'Causal')
    expect(onActualizarMapeo).toHaveBeenCalledWith('causal', 'Causal')
  })
})
