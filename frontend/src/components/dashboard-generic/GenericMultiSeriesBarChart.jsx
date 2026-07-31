import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatNumber } from '../../utils/format'
import { propsLeyendaPara } from '../../utils/legendPosition'
import { PALETA_CATEGORICA } from '../../utils/colors'

function acortar(texto, max = 22) {
  if (!texto) return ''
  return texto.length > max ? `${texto.slice(0, max)}…` : texto
}

/**
 * Renderiza un componente type=chart de varias series (`{titulo, categorias, series: [{nombre,
 * valores}]}`, ver `services/generic_charts.py::generar_datos_multiserie`) como barras agrupadas
 * (una barra por serie, lado a lado) o apiladas (`apilado=true`, todas las series en una sola
 * barra por categoría). Cada serie tiene su propio color, editable individualmente
 * (`override.colores.coloresPorSerie`).
 */
export default function GenericMultiSeriesBarChart({ data, override, apilado = false, leyendaPosicion }) {
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
        <BarChart data={datosGrafico} margin={{ left: 8, right: 24, bottom: 32 }}>
          <CartesianGrid stroke="var(--gridline)" />
          <XAxis dataKey="etiqueta" angle={-30} textAnchor="end" interval={0} height={50} />
          <YAxis tickFormatter={(v) => formatNumber(v)} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend {...propsLeyendaPara(leyendaPosicion)} />
          {data.series.map((serie, i) => (
            <Bar
              key={serie.nombre}
              dataKey={serie.nombre}
              stackId={apilado ? 'a' : undefined}
              fill={coloresPorSerie[serie.nombre] || PALETA_CATEGORICA[i % PALETA_CATEGORICA.length]}
              radius={apilado ? undefined : [4, 4, 0, 0]}
              maxBarSize={40}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
