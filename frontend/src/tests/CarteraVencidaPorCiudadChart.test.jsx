import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CarteraVencidaPorCiudadChart from '../components/charts/CarteraVencidaPorCiudadChart'
import { DrilldownProvider, useDrilldown } from '../hooks/useDrilldown'

const data = {
  total_vencida: 302687.53,
  ciudades: [
    { ciudad: 'QUITO', saldo_vencido: 181157.46, porcentaje: 59.85, porcentaje_acumulado: 59.85, documentos: 434, clientes: 245 },
    { ciudad: 'GUAYAQUIL', saldo_vencido: 121530.07, porcentaje: 40.15, porcentaje_acumulado: 100, documentos: 153, clientes: 82 },
  ],
}

function EstadoDebug() {
  const { abierto, titulo, filtrosDrilldown } = useDrilldown()
  return <div data-testid="estado">{abierto ? `${titulo}|${JSON.stringify(filtrosDrilldown)}` : 'CERRADO'}</div>
}

function renderConProvider(elemento) {
  return render(<DrilldownProvider>{elemento}<EstadoDebug /></DrilldownProvider>)
}

describe('CarteraVencidaPorCiudadChart', () => {
  it('no muestra la gráfica de Pareto (no existe porcentaje acumulado en pantalla)', () => {
    renderConProvider(<CarteraVencidaPorCiudadChart data={data} />)
    expect(screen.queryByText(/pareto/i)).not.toBeInTheDocument()
  })

  it('muestra el titulo del gráfico de pastel y el total considerado', () => {
    renderConProvider(<CarteraVencidaPorCiudadChart data={data} />)
    expect(screen.getByText('Cartera vencida por ciudad')).toBeInTheDocument()
    expect(screen.getByText(/\$ 302\.687,53/)).toBeInTheDocument()
  })

  it('muestra una leyenda con todas las ciudades, su monto y su participación', () => {
    renderConProvider(<CarteraVencidaPorCiudadChart data={data} />)
    expect(screen.getByLabelText('Leyenda de ciudades')).toBeInTheDocument()
    expect(screen.getByText('QUITO')).toBeInTheDocument()
    expect(screen.getByText('GUAYAQUIL')).toBeInTheDocument()
    expect(screen.getByText(/59,85%/)).toBeInTheDocument()
  })

  it('al seleccionar una ciudad de la leyenda abre el detalle con estado_cartera=VENCIDA y la ciudad', async () => {
    renderConProvider(<CarteraVencidaPorCiudadChart data={data} />)

    await userEvent.click(screen.getByText('QUITO'))

    const texto = screen.getByTestId('estado').textContent
    expect(texto).toContain('Cartera vencida de QUITO')
    expect(texto).toContain('"estado_cartera":"VENCIDA"')
    expect(texto).toContain('"ciudad":"QUITO"')
  })

  it('agrupa en "Otras ciudades" cuando hay más de 8 y permite ver el detalle agrupado', async () => {
    const muchasCiudades = {
      total_vencida: 1000,
      ciudades: Array.from({ length: 10 }, (_, i) => ({
        ciudad: `CIUDAD_${i}`, saldo_vencido: 100 - i, porcentaje: 10 - i, porcentaje_acumulado: 0, documentos: 1, clientes: 1,
      })),
      ciudades_agrupadas: [
        ...Array.from({ length: 8 }, (_, i) => ({
          ciudad: `CIUDAD_${i}`, saldo_vencido: 100 - i, porcentaje: 10 - i, porcentaje_acumulado: 0, documentos: 1, clientes: 1,
        })),
        {
          ciudad: 'OTRAS CIUDADES', saldo_vencido: 35, porcentaje: 3, porcentaje_acumulado: 100, documentos: 2, clientes: 2,
          ciudades_incluidas: ['CIUDAD_8', 'CIUDAD_9'],
        },
      ],
    }

    renderConProvider(<CarteraVencidaPorCiudadChart data={muchasCiudades} />)
    expect(screen.getByText('OTRAS CIUDADES')).toBeInTheDocument()

    await userEvent.click(screen.getByText('OTRAS CIUDADES'))
    const texto = screen.getByTestId('estado').textContent
    expect(texto).toContain('"ciudad":"CIUDAD_8,CIUDAD_9"')
  })

  it('muestra un estado sin datos cuando no hay cartera vencida', () => {
    renderConProvider(<CarteraVencidaPorCiudadChart data={{ total_vencida: 0, ciudades: [] }} />)
    expect(screen.getByText(/no hay cartera vencida/i)).toBeInTheDocument()
  })
})
