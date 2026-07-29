import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecuperadorCausalMatrix from '../components/charts/RecuperadorCausalMatrix'
import { DrilldownProvider, useDrilldown } from '../hooks/useDrilldown'

const matriz = {
  filas: ['R01 Maria Perez', 'R02 Luis Cordero'],
  columnas: ['GESTIONANDO', 'SIN GESTIÓN'],
  celdas: { 'R01 Maria Perez': { GESTIONANDO: 1000, 'SIN GESTIÓN': 300 }, 'R02 Luis Cordero': { GESTIONANDO: 2500 } },
  totales_fila: { 'R01 Maria Perez': 1300, 'R02 Luis Cordero': 2600 },
  totales_columna: { GESTIONANDO: 3500, 'SIN GESTIÓN': 300 },
  total_general: 3800,
  porcentajes_gestion: {
    'R01 Maria Perez': { porcentaje_gestionado: 76.92, porcentaje_sin_gestion: 23.08 },
    'R02 Luis Cordero': { porcentaje_gestionado: 100, porcentaje_sin_gestion: 0 },
  },
}

function EstadoDebug() {
  const { abierto, titulo, filtrosDrilldown } = useDrilldown()
  return <div data-testid="estado">{abierto ? `${titulo}|${JSON.stringify(filtrosDrilldown)}` : 'CERRADO'}</div>
}

function renderConProvider(elemento) {
  return render(<DrilldownProvider>{elemento}<EstadoDebug /></DrilldownProvider>)
}

describe('RecuperadorCausalMatrix', () => {
  it('al seleccionar una celda abre el detalle con recuperador y causal', async () => {
    renderConProvider(<RecuperadorCausalMatrix matriz={matriz} metrica="saldo" />)

    const celdas = screen.getAllByText('$ 1.000,00')
    await userEvent.click(celdas[0])

    const texto = screen.getByTestId('estado').textContent
    expect(texto).toContain('"recuperador":"R01 Maria Perez"')
    expect(texto).toContain('"causal":"GESTIONANDO"')
  })

  it('al seleccionar un total de fila abre el detalle solo por ese recuperador', async () => {
    renderConProvider(<RecuperadorCausalMatrix matriz={matriz} metrica="saldo" />)

    await userEvent.click(screen.getByText('$ 2.600,00'))

    const texto = screen.getByTestId('estado').textContent
    expect(texto).toContain('"recuperador":"R02 Luis Cordero"')
    expect(texto).not.toContain('causal')
  })

  it('la celda es navegable y activable por teclado', async () => {
    renderConProvider(<RecuperadorCausalMatrix matriz={matriz} metrica="saldo" />)

    const celda = screen.getAllByText('$ 1.000,00')[0].closest('[role="button"]')
    celda.focus()
    await userEvent.keyboard('{Enter}')

    expect(screen.getByTestId('estado').textContent).toContain('R01 Maria Perez')
  })
})
