import KpiCard from '../kpi/KpiCard'
import { formatNumber } from '../../utils/format'

/**
 * Renderiza un componente type=kpi generado dinámicamente por `establecer_componentes_generados`
 * (backend) — `data` es `component.content` tal cual viene del layout: `{titulo, valor}`.
 */
export default function GenericKpiCard({ data, override }) {
  if (!data) return null
  return (
    <KpiCard
      label={override?.titulo || data.titulo}
      value={formatNumber(data.valor)}
      sub={override?.descripcion || data.descripcion || undefined}
      accentColor={override?.colores?.colorPrincipal}
    />
  )
}
