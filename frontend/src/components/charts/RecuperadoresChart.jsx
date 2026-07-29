import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useDrilldown } from '../../hooks/useDrilldown'
import { formatCurrency, formatNumber, formatPercent } from '../../utils/format'

function TooltipPersonalizado({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="chart-panel" style={{ padding: 10 }}>
      <strong>{d.recuperador}</strong>
      <div>Saldo total: {formatCurrency(d.saldo_total)}</div>
      <div>Saldo vencido: {formatCurrency(d.saldo_vencido)} ({formatPercent(d.porcentaje_vencido)})</div>
      <div>Saldo no vencido: {formatCurrency(d.saldo_no_vencido)}</div>
      <div>Clientes: {formatNumber(d.clientes)} · Documentos: {formatNumber(d.documentos)}</div>
      <div>Documentos sin gestión: {formatNumber(d.documentos_sin_gestion)}</div>
      <div className="chart-panel__subtitle mb-0">Pulse para ver el detalle</div>
    </div>
  )
}

export default function RecuperadoresChart({ data, override }) {
  const { abrirDetalle } = useDrilldown()
  const datos = [...(data || [])].reverse()
  const mayor = data?.[0]
  const colorPrincipal = override?.colores?.colorPrincipal || 'var(--series-1)'

  const seleccionar = (entry) => {
    abrirDetalle({
      origen: 'saldo_por_recuperador',
      titulo: `Cartera de ${entry.recuperador}`,
      filtros: { recuperador: entry.recuperador },
    })
  }

  return (
    <div className="chart-panel">
      <div className="chart-panel__title">{override?.titulo || 'Saldo pendiente por recuperador'}</div>
      <div className="chart-panel__subtitle">
        {override?.descripcion || (mayor ? <>Recuperador con mayor saldo pendiente: <strong>{mayor.recuperador}</strong></> : 'Sin datos')}
      </div>
      <div className="chart-panel__subtitle" style={{ marginTop: -8 }}>
        No debe interpretarse como evaluación definitiva de desempeño: cada cartera tiene distinto tamaño y antigüedad.
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={datos} layout="vertical" margin={{ left: 8, right: 24 }}>
          <CartesianGrid horizontal={false} stroke="var(--gridline)" />
          <XAxis type="number" tickFormatter={(v) => formatCurrency(v)} />
          <YAxis type="category" dataKey="recuperador" width={160} tick={{ fontSize: 12 }} />
          <Tooltip content={<TooltipPersonalizado />} />
          <Bar dataKey="saldo_total" radius={[0, 4, 4, 0]} maxBarSize={22} onClick={seleccionar} cursor="pointer">
            {datos.map((d) => (
              <Cell key={d.recuperador} fill={d.es_mayor_saldo_pendiente ? 'var(--series-2)' : colorPrincipal} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
