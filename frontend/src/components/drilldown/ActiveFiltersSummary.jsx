import { Badge } from 'react-bootstrap'

const ETIQUETAS_FILTRO = {
  cliente: 'Cliente/RUC',
  ciudad: 'Ciudad',
  zona: 'Zona',
  sucursal: 'Sucursal',
  recuperador: 'Recuperador',
  causal: 'Causal',
  estado_cartera: 'Estado de cartera',
  rango_mora: 'Rango de mora',
  producto: 'Producto',
  articulo: 'Artículo',
  tipo_venta: 'Tipo de venta',
  estado_cliente: 'Estado del cliente',
  dias_vencidos_min: 'Días vencidos desde',
  dias_vencidos_max: 'Días vencidos hasta',
}

function etiquetaDe(campo) {
  return ETIQUETAS_FILTRO[campo] || campo
}

/**
 * Lista de filtros activos como chips. Los de `filtrosDrilldown` son removibles (los generó
 * la selección de un gráfico); los de `filtrosGlobales` solo se muestran como contexto y se
 * gestionan desde el panel de filtros del dashboard, no desde aquí.
 */
export default function ActiveFiltersSummary({ filtrosGlobales = {}, filtrosDrilldown = {}, onQuitarFiltro }) {
  const globalesActivos = Object.entries(filtrosGlobales).filter(([, v]) => v);
  const drilldownActivos = Object.entries(filtrosDrilldown).filter(([, v]) => v);

  if (globalesActivos.length === 0 && drilldownActivos.length === 0) {
    return <div className="chart-panel__subtitle mb-2">Sin filtros aplicados.</div>
  }

  return (
    <div className="d-flex flex-wrap gap-2 mb-2" aria-label="Filtros aplicados">
      {drilldownActivos.map(([campo, valor]) => (
        <Badge
          key={campo}
          bg="primary"
          className="d-flex align-items-center gap-1"
          style={{ fontSize: '0.8rem', padding: '0.4rem 0.6rem' }}
        >
          {etiquetaDe(campo)}: {String(valor)}
          {onQuitarFiltro && (
            <button
              type="button"
              className="btn-close btn-close-white"
              style={{ fontSize: '0.55rem' }}
              aria-label={`Quitar filtro ${etiquetaDe(campo)}`}
              onClick={() => onQuitarFiltro(campo)}
            />
          )}
        </Badge>
      ))}
      {globalesActivos.map(([campo, valor]) => (
        <Badge key={campo} bg="secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.6rem' }}>
          {etiquetaDe(campo)}: {String(valor)}
        </Badge>
      ))}
    </div>
  )
}
