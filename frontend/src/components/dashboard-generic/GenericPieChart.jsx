import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { formatNumber } from '../../utils/format'
import { propsLeyendaPara } from '../../utils/legendPosition'
import { PALETA_CATEGORICA } from '../../utils/colors'

/**
 * Renderiza un componente type=chart de una sola serie (`{titulo, categorias, valores}`) como
 * pastel o dona (`dona=true`, con un agujero central) — cada categoría es una porción, con su
 * propio color editable individualmente (`override.colores.coloresPorCategoria`).
 */
export default function GenericPieChart({ data, override, dona = false, leyendaPosicion }) {
  if (!data) return null
  const datosGrafico = (data.categorias || []).map((categoria, i) => ({
    nombre: categoria, valor: data.valores?.[i] ?? 0,
  }))
  const coloresPorCategoria = override?.colores?.coloresPorCategoria || {}

  return (
    <div className="chart-panel" style={override?.colores?.colorFondo ? { background: override.colores.colorFondo } : undefined}>
      <div className="chart-panel__title" style={override?.colores?.colorTexto ? { color: override.colores.colorTexto } : undefined}>
        {override?.titulo || data.titulo}
      </div>
      {(override?.descripcion || data.descripcion) && (
        <div className="chart-panel__subtitle">{override?.descripcion || data.descripcion}</div>
      )}
      <ResponsiveContainer width="100%" height={340}>
        <PieChart>
          <Pie
            data={datosGrafico}
            dataKey="valor"
            nameKey="nombre"
            innerRadius={dona ? '55%' : 0}
            outerRadius="80%"
            paddingAngle={dona ? 2 : 0}
          >
            {datosGrafico.map((entrada, i) => (
              <Cell key={entrada.nombre} fill={coloresPorCategoria[entrada.nombre] || PALETA_CATEGORICA[i % PALETA_CATEGORICA.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend {...propsLeyendaPara(leyendaPosicion)} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
