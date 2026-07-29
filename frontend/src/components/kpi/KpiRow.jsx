import { Col, Row } from 'react-bootstrap'
import KpiCard from './KpiCard'
import { useDrilldown } from '../../hooks/useDrilldown'
import { formatCurrency, formatDate, formatNumber, formatPercent } from '../../utils/format'

const COLORES = {
  neutral: 'var(--series-1)',
  good: 'var(--status-good)',
  warning: 'var(--status-warning)',
  serious: 'var(--status-serious)',
  critical: 'var(--status-critical)',
}

/**
 * Cada tarjeta KPI se exporta también como componente individual (además del `KpiRow`
 * ensamblado de siempre) porque el editor visual las trata como componentes de grid
 * independientes, arrastrables/ocultables por separado (sección 8). `override` (opcional) trae
 * `{ titulo, colorPrincipal }` desde la configuración del dashboard.
 */
export function KpiClientesUnicos({ kpis, override }) {
  const { abrirDetalle } = useDrilldown()
  if (!kpis) return null
  return (
    <KpiCard
      label={override?.titulo || 'Clientes únicos'}
      value={formatNumber(kpis.total_clientes)}
      sub={`${formatNumber(kpis.total_documentos)} documentos · promedio ${formatCurrency(kpis.saldo_promedio_por_cliente)}`}
      accentColor={override?.colores?.colorPrincipal || COLORES.neutral}
      onClick={() => abrirDetalle({ origen: 'kpi_clientes', titulo: 'Todos los clientes', filtros: {} })}
    />
  )
}

export function KpiCarteraTotal({ kpis, override }) {
  const { abrirDetalle } = useDrilldown()
  if (!kpis) return null
  return (
    <KpiCard
      label={override?.titulo || 'Cartera total'}
      value={formatCurrency(kpis.cartera_total)}
      sub={`Corte al ${formatDate(kpis.fecha_corte)}`}
      accentColor={override?.colores?.colorPrincipal || COLORES.neutral}
      onClick={() => abrirDetalle({ origen: 'kpi_cartera_total', titulo: 'Cartera total', filtros: {} })}
    />
  )
}

export function KpiCarteraVencida({ kpis, override }) {
  const { abrirDetalle } = useDrilldown()
  if (!kpis) return null
  return (
    <KpiCard
      label={override?.titulo || 'Cartera vencida'}
      value={formatCurrency(kpis.cartera_vencida.valor)}
      sub={`${formatPercent(kpis.cartera_vencida.porcentaje)} del total`}
      accentColor={override?.colores?.colorPrincipal || COLORES.warning}
      onClick={() => abrirDetalle({
        origen: 'kpi_cartera_vencida', titulo: 'Cartera vencida', filtros: { estado_cartera: 'VENCIDA' },
      })}
    />
  )
}

export function KpiCarteraNoVencida({ kpis, override }) {
  const { abrirDetalle } = useDrilldown()
  if (!kpis) return null
  const sinFecha = kpis.sin_fecha_vencimiento
  return (
    <KpiCard
      label={override?.titulo || 'Cartera no vencida'}
      value={formatCurrency(kpis.cartera_no_vencida.valor)}
      sub={`${formatPercent(kpis.cartera_no_vencida.porcentaje)} del total${sinFecha?.valor ? ` · ${formatPercent(sinFecha.porcentaje)} sin fecha` : ''}`}
      accentColor={override?.colores?.colorPrincipal || COLORES.good}
      onClick={() => abrirDetalle({
        origen: 'kpi_cartera_no_vencida', titulo: 'Cartera no vencida', filtros: { estado_cartera: 'NO VENCIDA' },
      })}
    />
  )
}

export function KpiMayor120({ kpis, override }) {
  const { abrirDetalle } = useDrilldown()
  if (!kpis) return null
  return (
    <KpiCard
      label={override?.titulo || 'Cartera > 120 días'}
      value={formatCurrency(kpis.mayor_120_dias.valor)}
      sub={`${formatPercent(kpis.mayor_120_dias.porcentaje)} · ${formatNumber(kpis.mayor_120_dias.clientes)} clientes · ${formatNumber(kpis.mayor_120_dias.documentos)} docs`}
      accentColor={override?.colores?.colorPrincipal || COLORES.serious}
      onClick={() => abrirDetalle({
        origen: 'kpi_mayor_120',
        titulo: 'Cartera con mora mayor a 120 días',
        filtros: { estado_cartera: 'VENCIDA', dias_vencidos_min: 121 },
      })}
    />
  )
}

export function KpiMayor360({ kpis, override }) {
  const { abrirDetalle } = useDrilldown()
  if (!kpis) return null
  return (
    <KpiCard
      label={override?.titulo || 'Cartera > 360 días'}
      value={formatCurrency(kpis.mayor_360_dias.valor)}
      sub={`${formatPercent(kpis.mayor_360_dias.porcentaje)} · ${formatNumber(kpis.mayor_360_dias.clientes)} clientes · ${formatNumber(kpis.mayor_360_dias.documentos)} docs`}
      accentColor={override?.colores?.colorPrincipal || COLORES.critical}
      onClick={() => abrirDetalle({
        origen: 'kpi_mayor_360',
        titulo: 'Cartera con mora mayor a 360 días',
        filtros: { estado_cartera: 'VENCIDA', dias_vencidos_min: 361 },
      })}
    />
  )
}

export default function KpiRow({ kpis }) {
  if (!kpis) return null

  return (
    <Row className="g-3 mb-2">
      <Col md={4} lg={2}><KpiClientesUnicos kpis={kpis} /></Col>
      <Col md={4} lg={2}><KpiCarteraTotal kpis={kpis} /></Col>
      <Col md={4} lg={2}><KpiCarteraVencida kpis={kpis} /></Col>
      <Col md={4} lg={2}><KpiCarteraNoVencida kpis={kpis} /></Col>
      <Col md={4} lg={2}><KpiMayor120 kpis={kpis} /></Col>
      <Col md={4} lg={2}><KpiMayor360 kpis={kpis} /></Col>
    </Row>
  )
}
