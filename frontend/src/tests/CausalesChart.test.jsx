import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CausalesChart from '../components/charts/CausalesChart'
import { DrilldownProvider, useDrilldown } from '../hooks/useDrilldown'

const data = {
  saldo_total: 1000,
  documentos_total: 10,
  causales: [
    { causal: 'GESTIONANDO', saldo: 700, porcentaje_monetario: 70, documentos: 7, porcentaje_documentos: 70 },
    { causal: 'SIN GESTIÓN', saldo: 300, porcentaje_monetario: 30, documentos: 3, porcentaje_documentos: 30 },
  ],
}

function EstadoDebug() {
  const { abierto, titulo, filtrosDrilldown } = useDrilldown()
  return <div data-testid="estado">{abierto ? `${titulo}|${JSON.stringify(filtrosDrilldown)}` : 'CERRADO'}</div>
}

function renderConProvider(elemento) {
  return render(<DrilldownProvider>{elemento}<EstadoDebug /></DrilldownProvider>)
}

describe('CausalesChart', () => {
  it('al seleccionar Gestionado desde la leyenda abre el detalle con ese causal', async () => {
    renderConProvider(<CausalesChart data={data} />)

    const botonGestionando = screen.getAllByText('GESTIONANDO')[0].closest('button')
    await userEvent.click(botonGestionando)

    const texto = screen.getByTestId('estado').textContent
    expect(texto).toContain('"causal":"GESTIONANDO"')
  })
})
