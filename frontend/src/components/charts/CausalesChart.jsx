import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Form } from 'react-bootstrap'
import { useDrilldown } from '../../hooks/useDrilldown'
import { colorPorIdentidad } from '../../utils/colors'
import { formatCurrency, formatNumber, formatPercent } from '../../utils/format'

function TooltipDona({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="chart-panel" style={{ padding: 10 }}>
      <strong>{d.causal}</strong>
      <div>Saldo: {formatCurrency(d.saldo)} ({formatPercent(d.porcentaje_monetario)})</div>
      <div>Documentos: {formatNumber(d.documentos)} ({formatPercent(d.porcentaje_documentos)})</div>
      <div className="chart-panel__subtitle mb-0">Pulse para ver el detalle</div>
    </div>
  )
}

export default function CausalesChart({ data, override }) {
  const [verTodas, setVerTodas] = useState(false)
  const { abrirDetalle } = useDrilldown()

  if (!data) return null

  const tieneAgrupadas = Boolean(data.causales_agrupadas)
  const conjunto = verTodas || !tieneAgrupadas ? data.causales : data.causales_agrupadas

  // "SIN GESTIÓN" es la única categoría con un color configurable explícito (sección 4.3); el
  // resto sigue asignado por identidad para no perder la consistencia entre gráficos.
  const colorDe = (causal) => {
    if (causal === 'SIN GESTIÓN' && override?.colores?.colorSinGestion) return override.colores.colorSinGestion
    return colorPorIdentidad(causal)
  }

  const seleccionar = (entry) => {
    if (entry.causal === 'OTRAS') {
      abrirDetalle({
        origen: 'estado_general_cartera',
        titulo: 'Cartera — Otras causales',
        filtros: { causal: entry.causales_incluidas.join(',') },
      })
      return
    }
    abrirDetalle({
      origen: 'estado_general_cartera',
      titulo: `Cartera con causal ${entry.causal}`,
      filtros: { causal: entry.causal },
    })
  }

  return (
    <div className="chart-panel">
      <div className="d-flex justify-content-between align-items-start">
        <div>
          <div className="chart-panel__title">{override?.titulo || 'Estado general de la cartera por causal'}</div>
          <div className="chart-panel__subtitle">{override?.descripcion || 'Los saldos vacíos se agrupan como SIN GESTIÓN.'}</div>
        </div>
        {tieneAgrupadas && (
          <Form.Check
            type="switch"
            label="Ver todas"
            checked={verTodas}
            onChange={(e) => setVerTodas(e.target.checked)}
          />
        )}
      </div>

      <div className="row">
        <div className="col-md-6">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={conjunto}
                dataKey="saldo"
                nameKey="causal"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={2}
                onClick={seleccionar}
                cursor="pointer"
              >
                {conjunto.map((c) => <Cell key={c.causal} fill={colorDe(c.causal)} />)}
              </Pie>
              <Tooltip content={<TooltipDona />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="col-md-6">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={conjunto} layout="vertical" margin={{ left: 8, right: 24 }}>
              <CartesianGrid horizontal={false} stroke="var(--gridline)" />
              <XAxis type="number" tickFormatter={(v) => formatCurrency(v)} />
              <YAxis type="category" dataKey="causal" width={110} tick={{ fontSize: 11 }} />
              <Tooltip content={<TooltipDona />} />
              <Bar dataKey="saldo" radius={[0, 4, 4, 0]} maxBarSize={18} onClick={seleccionar} cursor="pointer">
                {conjunto.map((c) => <Cell key={c.causal} fill={colorDe(c.causal)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="d-flex flex-wrap gap-3 mt-2" aria-label="Leyenda de causales">
        {conjunto.map((c) => (
          <button
            key={c.causal}
            type="button"
            className="d-flex align-items-center gap-1 border-0 bg-transparent p-0"
            style={{ fontSize: '0.8rem', cursor: 'pointer' }}
            onClick={() => seleccionar(c)}
            title={`${c.causal} — Pulse para ver el detalle`}
          >
            <span style={{ width: 10, height: 10, borderRadius: 2, background: colorDe(c.causal), display: 'inline-block' }} />
            <span className="text-secondary">{c.causal}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
