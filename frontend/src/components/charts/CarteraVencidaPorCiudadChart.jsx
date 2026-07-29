import { useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Form } from 'react-bootstrap'
import { useDrilldown } from '../../hooks/useDrilldown'
import { colorPorIdentidad } from '../../utils/colors'
import { formatCurrency, formatNumber, formatPercent } from '../../utils/format'

const OTRAS_CIUDADES = 'OTRAS CIUDADES'

function TooltipPersonalizado({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="chart-panel" style={{ padding: 10 }}>
      <strong>{d.ciudad}</strong>
      <div>Cartera vencida: {formatCurrency(d.saldo_vencido)}</div>
      <div>Participación: {formatPercent(d.porcentaje)}</div>
      <div className="chart-panel__subtitle mb-0">Pulse para ver el detalle</div>
    </div>
  )
}

/**
 * Gráfico de pastel de cartera vencida por ciudad (reemplaza el Pareto anterior). Cada
 * segmento y cada fila de la leyenda son seleccionables (mouse y teclado) y abren el panel de
 * detalle filtrado por `estado_cartera=VENCIDA` + `ciudad` — o, para "Otras ciudades", por la
 * lista completa de ciudades agrupadas.
 */
export default function CarteraVencidaPorCiudadChart({ data, override }) {
  const [verTodas, setVerTodas] = useState(false)
  const { abrirDetalle } = useDrilldown()

  const tituloBase = override?.titulo || 'Cartera vencida por ciudad'
  const ciudades = data?.ciudades || []
  const tieneAgrupadas = Boolean(data?.ciudades_agrupadas)
  const conjunto = verTodas || !tieneAgrupadas ? ciudades : data.ciudades_agrupadas

  if (ciudades.length === 0) {
    return (
      <div className="chart-panel">
        <div className="chart-panel__title">{tituloBase}</div>
        <div className="chart-panel__subtitle mb-0">No hay cartera vencida con los filtros actuales.</div>
      </div>
    )
  }

  const seleccionar = (entry) => {
    if (entry.ciudad === OTRAS_CIUDADES) {
      abrirDetalle({
        origen: 'cartera_vencida_por_ciudad',
        titulo: 'Cartera vencida — Otras ciudades',
        filtros: { estado_cartera: 'VENCIDA', ciudad: entry.ciudades_incluidas.join(',') },
      })
      return
    }
    abrirDetalle({
      origen: 'cartera_vencida_por_ciudad',
      titulo: `Cartera vencida de ${entry.ciudad}`,
      filtros: { estado_cartera: 'VENCIDA', ciudad: entry.ciudad },
    })
  }

  return (
    <div className="chart-panel">
      <div className="d-flex justify-content-between align-items-start flex-wrap gap-2">
        <div>
          <div className="chart-panel__title">{tituloBase}</div>
          <div className="chart-panel__subtitle">
            {override?.descripcion || `Total considerado: ${formatCurrency(data.total_vencida)}. Seleccione una ciudad para ver su detalle.`}
          </div>
        </div>
        {tieneAgrupadas && (
          <Form.Check type="switch" label="Ver todas" checked={verTodas} onChange={(e) => setVerTodas(e.target.checked)} />
        )}
      </div>

      <div className="row align-items-center">
        <div className="col-md-6">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={conjunto}
                dataKey="saldo_vencido"
                nameKey="ciudad"
                innerRadius={55}
                outerRadius={100}
                paddingAngle={2}
                onClick={seleccionar}
                cursor="pointer"
              >
                {conjunto.map((c) => <Cell key={c.ciudad} fill={colorPorIdentidad(c.ciudad)} />)}
              </Pie>
              <Tooltip content={<TooltipPersonalizado />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="col-md-6">
          <ul className="list-unstyled mb-0" aria-label="Leyenda de ciudades">
            {conjunto.map((c) => (
              <li key={c.ciudad} className="mb-1">
                <button
                  type="button"
                  className="btn btn-sm w-100 d-flex align-items-center gap-2 text-start border-0"
                  style={{ background: 'transparent' }}
                  onClick={() => seleccionar(c)}
                  title={`${c.ciudad}: ${formatCurrency(c.saldo_vencido)} — Pulse para ver el detalle`}
                >
                  <span
                    aria-hidden="true"
                    style={{ width: 12, height: 12, borderRadius: 3, background: colorPorIdentidad(c.ciudad), display: 'inline-block', flexShrink: 0 }}
                  />
                  <span className="flex-grow-1 text-truncate">{c.ciudad}</span>
                  <span className="text-secondary" style={{ fontSize: '0.85rem' }}>
                    {formatCurrency(c.saldo_vencido)} — {formatPercent(c.porcentaje)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
