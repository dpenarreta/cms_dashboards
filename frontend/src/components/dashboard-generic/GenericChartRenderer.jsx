import GenericKpiCard from './GenericKpiCard'
import GenericBarChart from './GenericBarChart'
import GenericMultiSeriesBarChart from './GenericMultiSeriesBarChart'
import GenericStackedAreaChart from './GenericStackedAreaChart'
import GenericMultiLineChart from './GenericMultiLineChart'
import GenericLineChart from './GenericLineChart'
import GenericPieChart from './GenericPieChart'
import GenericDataTable from './GenericDataTable'
import GenericScatterChart from './GenericScatterChart'

/** Une varias series (`{categorias, series:[{nombre,valores}]}`, 2+ columnas de valor) en una
 * sola porción por categoría (`{categorias, valores}`, sumando las series de esa categoría) —
 * necesario porque un gráfico circular (pastel/dona) solo puede mostrar una cantidad por
 * categoría, nunca varias series a la vez, a diferencia de barras/líneas/área. */
function categoricoDesdeMultiserie(datosMultiserie) {
  if (!datosMultiserie?.categorias?.length || !datosMultiserie.series?.length) return null
  const valores = datosMultiserie.categorias.map((_, i) => (
    datosMultiserie.series.reduce((suma, serie) => suma + (serie.valores?.[i] || 0), 0)
  ))
  return { categorias: datosMultiserie.categorias, valores }
}

/**
 * Único punto que decide qué componente de presentación usar según `tipoVisualizacion` (uno de
 * `TIPOS_VISUALIZACION`, ver `utils/chartTypes.js`) — usado tanto para la vista previa de una
 * recomendación (datos ya calculados, sin persistir todavía) como para renderizar un componente
 * ya agregado al dashboard (`component.chart_type`). Así "los gráficos sugeridos se pueden
 * visualizar de cualquiera de estas formas" sin duplicar la lógica de despacho en dos lugares.
 */
export default function GenericChartRenderer({ tipoVisualizacion, datos, datosMultiserie, titulo, override, config, esHistorica }) {
  // Pastel/dona son compatibles con posiciones de 2+ columnas de valor (`multivalor`/`multiserie`,
  // ver `utils/plantillaSlots.js::TIPOS_COMPATIBLES`) aunque su contenido calculado siga llegando
  // como `datosMultiserie` (varias series) — acá, y solo para estos dos tipos, se colapsa en una
  // sola porción por categoría en vez de pedirle al usuario que rehaga el mapeo a una columna.
  const esCircular = tipoVisualizacion === 'pastel' || tipoVisualizacion === 'dona'
  const datosCirculares = esCircular ? (datos || categoricoDesdeMultiserie(datosMultiserie)) : datos
  const datosConTitulo = datosCirculares ? { ...datosCirculares, titulo } : null
  const datosMultiserieConTitulo = datosMultiserie ? { ...datosMultiserie, titulo } : null
  const leyendaPosicion = config?.leyenda_posicion

  switch (tipoVisualizacion) {
    case 'kpi':
      return datosConTitulo ? <GenericKpiCard data={datosConTitulo} override={override} config={config} /> : null
    case 'barras_verticales':
      return <GenericBarChart data={datosConTitulo} override={override} orientacion="vertical" />
    case 'barras_agrupadas':
      return <GenericMultiSeriesBarChart data={datosMultiserieConTitulo} override={override} apilado={false} leyendaPosicion={leyendaPosicion} />
    case 'barras_apiladas':
      return <GenericMultiSeriesBarChart data={datosMultiserieConTitulo} override={override} apilado leyendaPosicion={leyendaPosicion} />
    case 'area_apilada':
      return <GenericStackedAreaChart data={datosMultiserieConTitulo} override={override} leyendaPosicion={leyendaPosicion} />
    case 'lineas_multiples':
      return <GenericMultiLineChart data={datosMultiserieConTitulo} override={override} leyendaPosicion={leyendaPosicion} />
    case 'lineas':
      return <GenericLineChart data={datosConTitulo} override={override} />
    case 'pastel':
      return <GenericPieChart data={datosConTitulo} override={override} leyendaPosicion={leyendaPosicion} />
    case 'dona':
      return <GenericPieChart data={datosConTitulo} override={override} dona leyendaPosicion={leyendaPosicion} mostrarTotal={Boolean(config?.mostrar_total)} />
    case 'tabla':
      return <GenericDataTable data={datosConTitulo} override={override} esHistorica={esHistorica} />
    case 'dispersion':
      return <GenericScatterChart data={datosConTitulo} override={override} />
    case 'barras_horizontales':
    default:
      return <GenericBarChart data={datosConTitulo} override={override} orientacion="horizontal" />
  }
}
