import GenericKpiCard from './GenericKpiCard'
import GenericBarChart from './GenericBarChart'
import GenericMultiSeriesBarChart from './GenericMultiSeriesBarChart'
import GenericStackedAreaChart from './GenericStackedAreaChart'
import GenericLineChart from './GenericLineChart'
import GenericPieChart from './GenericPieChart'
import GenericDataTable from './GenericDataTable'
import GenericScatterChart from './GenericScatterChart'

/**
 * Único punto que decide qué componente de presentación usar según `tipoVisualizacion` (uno de
 * `TIPOS_VISUALIZACION`, ver `utils/chartTypes.js`) — usado tanto para la vista previa de una
 * recomendación (datos ya calculados, sin persistir todavía) como para renderizar un componente
 * ya agregado al dashboard (`component.chart_type`). Así "los gráficos sugeridos se pueden
 * visualizar de cualquiera de estas formas" sin duplicar la lógica de despacho en dos lugares.
 */
export default function GenericChartRenderer({ tipoVisualizacion, datos, datosMultiserie, titulo, override, config }) {
  const datosConTitulo = datos ? { ...datos, titulo } : null
  const datosMultiserieConTitulo = datosMultiserie ? { ...datosMultiserie, titulo } : null
  const leyendaPosicion = config?.leyenda_posicion

  switch (tipoVisualizacion) {
    case 'kpi':
      return datosConTitulo ? <GenericKpiCard data={datosConTitulo} override={override} /> : null
    case 'barras_verticales':
      return <GenericBarChart data={datosConTitulo} override={override} orientacion="vertical" />
    case 'barras_agrupadas':
      return <GenericMultiSeriesBarChart data={datosMultiserieConTitulo} override={override} apilado={false} leyendaPosicion={leyendaPosicion} />
    case 'barras_apiladas':
      return <GenericMultiSeriesBarChart data={datosMultiserieConTitulo} override={override} apilado leyendaPosicion={leyendaPosicion} />
    case 'area_apilada':
      return <GenericStackedAreaChart data={datosMultiserieConTitulo} override={override} leyendaPosicion={leyendaPosicion} />
    case 'lineas':
      return <GenericLineChart data={datosConTitulo} override={override} />
    case 'pastel':
      return <GenericPieChart data={datosConTitulo} override={override} leyendaPosicion={leyendaPosicion} />
    case 'dona':
      return <GenericPieChart data={datosConTitulo} override={override} dona leyendaPosicion={leyendaPosicion} />
    case 'tabla':
      return <GenericDataTable data={datosConTitulo} override={override} />
    case 'dispersion':
      return <GenericScatterChart data={datosConTitulo} override={override} />
    case 'barras_horizontales':
    default:
      return <GenericBarChart data={datosConTitulo} override={override} orientacion="horizontal" />
  }
}
