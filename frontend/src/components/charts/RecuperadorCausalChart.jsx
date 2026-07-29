import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Form } from 'react-bootstrap'
import { useDrilldown } from '../../hooks/useDrilldown'
import { colorPorIdentidad } from '../../utils/colors'
import { formatCurrency, formatNumber, formatPercent } from '../../utils/format'

const ETIQUETA_METRICA = { saldo: 'Saldo', documentos: 'Documentos', clientes: 'Clientes' }

function formatearValor(metrica, valor) {
  return metrica === 'saldo' ? formatCurrency(valor) : formatNumber(valor)
}

function pivotar(data, metrica) {
  const porRecuperador = new Map()
  const causales = new Set()
  for (const fila of data || []) {
    causales.add(fila.causal)
    if (!porRecuperador.has(fila.recuperador)) {
      porRecuperador.set(fila.recuperador, { recuperador: fila.recuperador })
    }
    porRecuperador.get(fila.recuperador)[fila.causal] = fila[metrica]
  }
  return { filas: Array.from(porRecuperador.values()), causales: Array.from(causales) }
}

function crearTooltip(data, metrica) {
  const detalle = new Map()
  for (const fila of data || []) {
    detalle.set(`${fila.recuperador}__${fila.causal}`, fila)
  }

  return function TooltipPersonalizado({ active, payload, label }) {
    if (!active || !payload?.length) return null
    return (
      <div className="chart-panel" style={{ padding: 10, maxWidth: 280 }}>
        <strong>{label}</strong>
        {payload.filter((p) => p.value).map((p) => {
          const d = detalle.get(`${label}__${p.dataKey}`)
          return (
            <div key={p.dataKey} className="mt-1">
              <span style={{ width: 10, height: 10, background: p.fill, display: 'inline-block', marginRight: 4 }} />
              <strong>{p.dataKey}</strong>: {formatearValor(metrica, p.value)}
              {d && (
                <div className="chart-panel__subtitle mb-0">
                  {formatPercent(d.porcentaje_dentro_recuperador)} del recuperador · {formatPercent(d.porcentaje_sobre_total)} del total
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }
}

export default function RecuperadorCausalChart({ data, metrica, onCambiarMetrica, override }) {
  const { abrirDetalle } = useDrilldown()
  const { filas, causales } = pivotar(data, metrica)
  const TooltipPersonalizado = crearTooltip(data, metrica)

  const colorDe = (causal) => {
    if (causal === 'SIN GESTIÓN' && override?.colores?.colorSinGestion) return override.colores.colorSinGestion
    return colorPorIdentidad(causal)
  }

  const seleccionar = (causal) => (entry) => {
    abrirDetalle({
      origen: 'causales_por_recuperador',
      titulo: `${entry.recuperador} — ${causal}`,
      filtros: { recuperador: entry.recuperador, causal },
    })
  }

  return (
    <div className="chart-panel">
      <div className="d-flex justify-content-between align-items-start flex-wrap gap-2">
        <div>
          <div className="chart-panel__title">{override?.titulo || 'Causales por recuperador de cartera'}</div>
          <div className="chart-panel__subtitle">{override?.descripcion || 'SIN GESTIÓN y SIN RECUPERADOR ASIGNADO se muestran como categorías propias.'}</div>
        </div>
        <Form.Select
          size="sm"
          style={{ width: 'auto' }}
          value={metrica}
          onChange={(e) => onCambiarMetrica(e.target.value)}
        >
          {Object.entries(ETIQUETA_METRICA).map(([valor, etiqueta]) => (
            <option key={valor} value={valor}>{etiqueta}</option>
          ))}
        </Form.Select>
      </div>
      <ResponsiveContainer width="100%" height={340}>
        <BarChart data={filas} layout="vertical" margin={{ left: 8, right: 24 }}>
          <CartesianGrid horizontal={false} stroke="var(--gridline)" />
          <XAxis type="number" tickFormatter={(v) => formatearValor(metrica, v)} />
          <YAxis type="category" dataKey="recuperador" width={160} tick={{ fontSize: 12 }} />
          <Tooltip content={<TooltipPersonalizado />} />
          {causales.map((causal) => (
            <Bar
              key={causal}
              dataKey={causal}
              stackId="causales"
              fill={colorDe(causal)}
              maxBarSize={22}
              onClick={seleccionar(causal)}
              cursor="pointer"
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
