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

  it('pagina las filas de recuperadores sin afectar los totales del pie de tabla', async () => {
    const filas = Array.from({ length: 12 }, (_, i) => `R${i} Recuperador ${i}`)
    const celdas = Object.fromEntries(filas.map((r) => [r, { GESTIONANDO: 100, 'SIN GESTIÓN': 20 }]))
    const totalesFila = Object.fromEntries(filas.map((r) => [r, 120]))
    const matrizGrande = {
      filas,
      columnas: ['GESTIONANDO', 'SIN GESTIÓN'],
      celdas,
      totales_fila: totalesFila,
      totales_columna: { GESTIONANDO: 1200, 'SIN GESTIÓN': 240 },
      total_general: 1440,
      porcentajes_gestion: Object.fromEntries(filas.map((r) => [r, { porcentaje_gestionado: 83.33, porcentaje_sin_gestion: 16.67 }])),
    }

    renderConProvider(<RecuperadorCausalMatrix matriz={matrizGrande} metrica="saldo" />)

    // Página 1 con tamaño por defecto (10): se ven 10 filas, no las 12.
    expect(screen.getAllByText(/^R\d+ Recuperador \d+$/).length).toBe(10)
    // El total general del pie sigue reflejando las 12 filas completas.
    expect(screen.getByText('$ 1.440,00')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Página siguiente' }))
    expect(screen.getAllByText(/^R\d+ Recuperador \d+$/).length).toBe(2)
    expect(screen.getByText('$ 1.440,00')).toBeInTheDocument()
  })

  it('reinicia a la página 1 cuando cambia la matriz (nuevo filtro)', async () => {
    const filas = Array.from({ length: 15 }, (_, i) => `R${i}`)
    const matrizGrande = {
      filas,
      columnas: ['GESTIONANDO'],
      celdas: Object.fromEntries(filas.map((r) => [r, { GESTIONANDO: 10 }])),
      totales_fila: Object.fromEntries(filas.map((r) => [r, 10])),
      totales_columna: { GESTIONANDO: 150 },
      total_general: 150,
      porcentajes_gestion: Object.fromEntries(filas.map((r) => [r, { porcentaje_gestionado: 100, porcentaje_sin_gestion: 0 }])),
    }

    const { rerender } = renderConProvider(<RecuperadorCausalMatrix matriz={matrizGrande} metrica="saldo" />)
    await userEvent.click(screen.getByRole('button', { name: 'Página siguiente' }))
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument()

    const matrizFiltrada = { ...matrizGrande, filas: filas.slice(0, 3) }
    rerender(<DrilldownProvider><RecuperadorCausalMatrix matriz={matrizFiltrada} metrica="saldo" /><EstadoDebug /></DrilldownProvider>)

    expect(await screen.findByText('Página 1 de 1')).toBeInTheDocument()
  })
})
