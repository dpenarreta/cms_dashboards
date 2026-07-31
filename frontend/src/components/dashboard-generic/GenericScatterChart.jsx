import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts'
import { formatNumber } from '../../utils/format'

/**
 * Renderiza un componente type=chart de dispersión (`{titulo, puntos: [{x, y}]}`, ver
 * `services/generic_charts.py::generar_datos_dispersion`) — a diferencia del resto de gráficas
 * genéricas, no agrupa por categoría: cada punto es una fila del archivo con sus dos valores
 * numéricos (x, y). Un único color para todos los puntos (`override.colores.colorPrincipal`), ya
 * que no hay categorías que distinguir por color.
 */
export default function GenericScatterChart({ data, override }) {
  if (!data?.puntos?.length) return null
  const colorPrincipal = override?.colores?.colorPrincipal || 'var(--series-1)'

  return (
    <div className="chart-panel" style={override?.colores?.colorFondo ? { background: override.colores.colorFondo } : undefined}>
      <div className="chart-panel__title" style={override?.colores?.colorTexto ? { color: override.colores.colorTexto } : undefined}>
        {override?.titulo || data.titulo}
      </div>
      {(override?.descripcion || data.descripcion) && (
        <div className="chart-panel__subtitle">{override?.descripcion || data.descripcion}</div>
      )}
      <ResponsiveContainer width="100%" height={340}>
        <ScatterChart margin={{ left: 8, right: 24, bottom: 8 }}>
          <CartesianGrid stroke="var(--gridline)" />
          <XAxis type="number" dataKey="x" name="X" tickFormatter={(v) => formatNumber(v)} />
          <YAxis type="number" dataKey="y" name="Y" tickFormatter={(v) => formatNumber(v)} />
          <Tooltip formatter={(value) => formatNumber(value)} cursor={{ strokeDasharray: '3 3' }} />
          <Scatter data={data.puntos} fill={colorPrincipal} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}
