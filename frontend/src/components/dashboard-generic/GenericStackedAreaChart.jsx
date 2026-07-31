import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatNumber } from '../../utils/format'
import { propsLeyendaPara } from '../../utils/legendPosition'
import { PALETA_CATEGORICA } from '../../utils/colors'

function acortar(texto, max = 22) {
  if (!texto) return ''
  return texto.length > max ? `${texto.slice(0, max)}…` : texto
}

/**
 * Renderiza un componente type=chart de varias series (`{titulo, categorias, series: [{nombre,
 * valores}]}`, mismo dato que las barras agrupadas/apiladas — ver
 * `services/generic_charts.py::generar_datos_multiserie`) como un área apilada: cada serie es una
 * capa de color sobre la anterior, siempre apiladas (a diferencia de las barras, un área agrupada
 * sin apilar no se distingue visualmente). Cada serie tiene su propio color, editable
 * individualmente (`override.colores.coloresPorSerie`).
 */
export default function GenericStackedAreaChart({ data, override, leyendaPosicion }) {
  if (!data?.series?.length) return null

  const coloresPorSerie = override?.colores?.coloresPorSerie || {}
  const datosGrafico = (data.categorias || []).map((categoria, i) => {
    const fila = { categoria, etiqueta: acortar(categoria) }
    for (const serie of data.series) fila[serie.nombre] = serie.valores?.[i] ?? 0
    return fila
  })

  return (
    <div className="chart-panel" style={override?.colores?.colorFondo ? { background: override.colores.colorFondo } : undefined}>
      <div className="chart-panel__title" style={override?.colores?.colorTexto ? { color: override.colores.colorTexto } : undefined}>
        {override?.titulo || data.titulo}
      </div>
      {(override?.descripcion || data.descripcion) && (
        <div className="chart-panel__subtitle">{override?.descripcion || data.descripcion}</div>
      )}
      <ResponsiveContainer width="100%" height={340}>
        <AreaChart data={datosGrafico} margin={{ left: 8, right: 24, bottom: 32 }}>
          <CartesianGrid stroke="var(--gridline)" />
          <XAxis dataKey="etiqueta" angle={-30} textAnchor="end" interval={0} height={50} />
          <YAxis tickFormatter={(v) => formatNumber(v)} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend {...propsLeyendaPara(leyendaPosicion)} />
          {data.series.map((serie, i) => {
            const color = coloresPorSerie[serie.nombre] || PALETA_CATEGORICA[i % PALETA_CATEGORICA.length]
            return (
              <Area
                key={serie.nombre}
                type="monotone"
                dataKey={serie.nombre}
                stackId="a"
                stroke={color}
                fill={color}
                fillOpacity={0.6}
              />
            )
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
