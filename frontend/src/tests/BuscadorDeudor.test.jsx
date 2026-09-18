import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import BuscadorDeudor from '../components/dashboard-directorio/BuscadorDeudor'
import { buscarDeudores, obtenerDetalleDeudor } from '../services/dashboardLayoutService'

vi.mock('../services/dashboardLayoutService', () => ({
  buscarDeudores: vi.fn(),
  obtenerDetalleDeudor: vi.fn(),
}))

/**
 * Consulta puntual de un deudor.
 *
 * Lo que importa verificar acá es el comportamiento que decide la utilidad de la sección: que no
 * sume dos clientes distintos por una coincidencia parcial, y que un tramo sin documentos se vea
 * en 0 en vez de desaparecer (es información: dice que ese cliente no tiene mora en ese tramo).
 */

const COMPONENTE = {
  content: { titulo: 'CONSULTA POR CLIENTE' },
  mapeo: {
    columna_id: 'Cliente', columna_ruc: 'Ruc Cliente',
    columna_fecha: 'Fecha de Vencimiento', columna_valor: 'Saldo',
  },
  config: { bloque: 'consulta-deudor', columnas_detalle: ['Número de Documento', 'Saldo'] },
}

const DETALLE = {
  identidad: '111',
  nombre: 'TRANSEXPRESS',
  total: 1000,
  cantidad_filas: 2,
  tramos: {
    categorias: ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días'],
    valores: [800, 0, 0, 0, 0, 200],
  },
  columnas: ['Número de Documento', 'Saldo'],
  filas: [['A-1', 800], ['A-2', 200]],
}

function pintar() {
  return render(<BuscadorDeudor componente={COMPONENTE} dashboardId="directorio-cartera" />)
}

async function consultar(texto = 'transex') {
  const usuario = userEvent.setup()
  await usuario.type(screen.getByLabelText('Nombre o identificador del cliente'), texto)
  await usuario.click(screen.getByRole('button', { name: 'Consultar' }))
  return usuario
}

describe('BuscadorDeudor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('con una sola coincidencia abre el detalle directo, sin un clic que no decide nada', async () => {
    buscarDeudores.mockResolvedValue({ coincidencias: [{ identidad: '111', nombre: 'TRANSEXPRESS', saldo: 1000, filas: 2 }], total: 1 })
    obtenerDetalleDeudor.mockResolvedValue(DETALLE)
    pintar()
    await consultar()
    await waitFor(() => expect(screen.getByText(/TRANSEXPRESS —/)).toBeInTheDocument())
    expect(obtenerDetalleDeudor).toHaveBeenCalled()
  })

  it('con varias coincidencias hace elegir, en vez de sumar clientes distintos', async () => {
    buscarDeudores.mockResolvedValue({
      coincidencias: [
        { identidad: '111', nombre: 'TRANSEXPRESS', saldo: 1000, filas: 2 },
        { identidad: '222', nombre: 'TRANSEXPORT SA', saldo: 50, filas: 1 },
      ],
      total: 2,
    })
    pintar()
    await consultar()
    await waitFor(() => expect(screen.getByText('2 coincidencias — elegí una:')).toBeInTheDocument())
    expect(obtenerDetalleDeudor).not.toHaveBeenCalled()
    expect(screen.getByText('TRANSEXPORT SA')).toBeInTheDocument()
  })

  it('al elegir una de las coincidencias se pide su detalle', async () => {
    buscarDeudores.mockResolvedValue({
      coincidencias: [
        { identidad: '111', nombre: 'TRANSEXPRESS', saldo: 1000, filas: 2 },
        { identidad: '222', nombre: 'TRANSEXPORT SA', saldo: 50, filas: 1 },
      ],
      total: 2,
    })
    obtenerDetalleDeudor.mockResolvedValue(DETALLE)
    pintar()
    const usuario = await consultar()
    await waitFor(() => expect(screen.getByText('TRANSEXPORT SA')).toBeInTheDocument())
    await usuario.click(screen.getByText('TRANSEXPORT SA'))
    await waitFor(() => expect(obtenerDetalleDeudor).toHaveBeenCalledWith(
      'directorio-cartera', expect.objectContaining({ identidad: '222' }),
    ))
  })

  it('los tramos sin documentos se muestran en 0, no se ocultan', async () => {
    buscarDeudores.mockResolvedValue({ coincidencias: [{ identidad: '111', nombre: 'TRANSEXPRESS', saldo: 1000, filas: 2 }], total: 1 })
    obtenerDetalleDeudor.mockResolvedValue(DETALLE)
    pintar()
    await consultar()
    await waitFor(() => expect(screen.getByText('60 días')).toBeInTheDocument())
    // Los seis tramos están presentes aunque cuatro valgan cero.
    for (const tramo of ['Anticipada', '30 días', '60 días', '90 días', '120 días', '+120 días']) {
      expect(screen.getByText(tramo)).toBeInTheDocument()
    }
    expect(screen.getAllByText('$0').length).toBe(4)
  })

  it('el detalle muestra solo las columnas configuradas en el componente', async () => {
    buscarDeudores.mockResolvedValue({ coincidencias: [{ identidad: '111', nombre: 'TRANSEXPRESS', saldo: 1000, filas: 2 }], total: 1 })
    obtenerDetalleDeudor.mockResolvedValue(DETALLE)
    pintar()
    await consultar()
    await waitFor(() => expect(screen.getByText('NÚMERO DE DOCUMENTO')).toBeInTheDocument())
    expect(obtenerDetalleDeudor).toHaveBeenCalledWith('directorio-cartera', expect.objectContaining({
      columnasDetalle: ['Número de Documento', 'Saldo'],
    }))
  })

  it('un valor vacío se muestra como raya, no como "null"', async () => {
    buscarDeudores.mockResolvedValue({ coincidencias: [{ identidad: '111', nombre: 'TRANSEXPRESS', saldo: 1000, filas: 1 }], total: 1 })
    obtenerDetalleDeudor.mockResolvedValue({ ...DETALLE, filas: [['A-1', null]] })
    pintar()
    await consultar()
    await waitFor(() => expect(screen.getByText('A-1')).toBeInTheDocument())
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('sin coincidencias lo dice, en vez de dejar la sección en blanco', async () => {
    buscarDeudores.mockResolvedValue({ coincidencias: [], total: 0 })
    pintar()
    await consultar('inexistente')
    await waitFor(() => expect(screen.getByText(/No hay clientes que coincidan/)).toBeInTheDocument())
  })

  it('un error del backend se muestra con su mensaje', async () => {
    buscarDeudores.mockRejectedValue({ response: { data: { mensaje: 'Escribí al menos dos caracteres para buscar.' } } })
    pintar()
    await consultar('t')
    await waitFor(() => expect(screen.getByText('Escribí al menos dos caracteres para buscar.')).toBeInTheDocument())
  })

  it('las columnas del mapeo viajan en la consulta, para que la sección siga siendo reconfigurable', async () => {
    buscarDeudores.mockResolvedValue({ coincidencias: [], total: 0 })
    pintar()
    await consultar()
    expect(buscarDeudores).toHaveBeenCalledWith('directorio-cartera', expect.objectContaining({
      columnas: { nombre: 'Cliente', ruc: 'Ruc Cliente', fecha: 'Fecha de Vencimiento', valor: 'Saldo' },
    }))
  })
})
