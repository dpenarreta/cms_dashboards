import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import RecuperadoresChart from '../components/charts/RecuperadoresChart'
import { DrilldownProvider } from '../hooks/useDrilldown'

const data = [
  {
    recuperador: 'R02 Luis Cordero', saldo_total: 5000, saldo_vencido: 1000, saldo_no_vencido: 4000,
    porcentaje_vencido: 20, clientes: 10, documentos: 20, documentos_sin_gestion: 5, es_mayor_saldo_pendiente: true,
  },
  {
    recuperador: 'R01 Maria Perez', saldo_total: 3000, saldo_vencido: 500, saldo_no_vencido: 2500,
    porcentaje_vencido: 16.67, clientes: 8, documentos: 15, documentos_sin_gestion: 2, es_mayor_saldo_pendiente: false,
  },
]

describe('RecuperadoresChart', () => {
  it('identifica al recuperador con mayor saldo pendiente', () => {
    render(<DrilldownProvider><RecuperadoresChart data={data} /></DrilldownProvider>)
    expect(screen.getByText('R02 Luis Cordero')).toBeInTheDocument()
    expect(screen.getByText(/no debe interpretarse como evaluación definitiva/i)).toBeInTheDocument()
  })
})
