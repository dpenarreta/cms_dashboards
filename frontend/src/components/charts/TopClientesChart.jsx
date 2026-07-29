import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useDrilldown } from '../../hooks/useDrilldown'
import { formatCurrency, formatNumber, formatPercent } from '../../utils/format'

function acortar(texto, max = 22) {
  if (!texto) return ''
  return texto.length > max ? `${texto.slice(0, max)}…` : texto
}

function TooltipPersonalizado({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="chart-panel" style={{ padding: 10 }}>
      <strong>{d.cliente}</strong>
      <div className="chart-panel__subtitle mb-1">RUC: {d.ruc_cliente || '—'}</div>
      <div>Saldo total: {formatCurrency(d.saldo_total)}</div>
      <div>Saldo vencido: {formatCurrency(d.saldo_vencido)}</div>
      <div>Saldo no vencido: {formatCurrency(d.saldo_no_vencido)}</div>
      <div>Documentos: {formatNumber(d.documentos)}</div>
      <div>% sobre cartera total: {formatPercent(d.porcentaje_sobre_total)}</div>
      <div className="chart-panel__subtitle mb-0">Pulse para ver el detalle</div>
    </div>
  )
}

export default function TopClientesChart({ data, override }) {
  const { abrirDetalle } = useDrilldown()
  const datosGrafico = [...(data || [])].reverse().map((d) => ({ ...d, etiqueta: acortar(d.cliente) }))
  const colorPrincipal = override?.colores?.colorPrincipal || 'var(--series-1)'

  const seleccionarCliente = (entry) => {
    if (!entry?.ruc_cliente) return
    abrirDetalle({
      origen: 'top_clientes',
      titulo: `Documentos de ${entry.cliente}`,
      filtros: { cliente: entry.ruc_cliente },
    })
  }

  return (
    <div className="chart-panel" style={override?.colores?.colorFondo ? { background: override.colores.colorFondo } : undefined}>
      <div className="chart-panel__title" style={override?.colores?.colorTexto ? { color: override.colores.colorTexto } : undefined}>
        {override?.titulo || 'Top 10 clientes que más adeudan'}
      </div>
      <div className="chart-panel__subtitle">
        {override?.descripcion || 'Ordenado por saldo total descendente. Clic en una barra para ver el detalle.'}
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={datosGrafico} layout="vertical" margin={{ left: 8, right: 24 }}>
          <CartesianGrid horizontal={false} stroke="var(--gridline)" />
          <XAxis type="number" tickFormatter={(v) => formatCurrency(v)} />
          <YAxis type="category" dataKey="etiqueta" width={160} />
          <Tooltip content={<TooltipPersonalizado />} />
          <Bar
            dataKey="saldo_total"
            fill={colorPrincipal}
            radius={[0, 4, 4, 0]}
            maxBarSize={22}
            onClick={seleccionarCliente}
            cursor="pointer"
          >
            {datosGrafico.map((entry) => (
              <Cell key={entry.identificador_cliente} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
