import { useState } from 'react'
import { Button, Col, Collapse, Form, Row } from 'react-bootstrap'
import { formatCurrency, formatNumber, formatPercent } from '../../utils/format'

const ESTADOS_CARTERA = ['NO VENCIDA', 'VENCIDA', 'SIN FECHA DE VENCIMIENTO', 'SALDO CERO', 'SALDO A FAVOR']
const RANGOS_MORA = [
  'POR VENCER', '0-30 DÍAS', '31-60 DÍAS', '61-90 DÍAS', '91-120 DÍAS',
  '121-180 DÍAS', '181-360 DÍAS', 'MÁS DE 360 DÍAS', 'SIN FECHA',
]

const TIPO_POR_CAMPO = {
  cliente: 'texto', ciudad: 'texto', zona: 'texto', sucursal: 'texto',
  recuperador: 'select-recuperador', causal: 'select-causal',
  estado_cartera: 'select-estado-cartera', rango_mora: 'select-rango-mora',
  producto: 'texto', articulo: 'texto', tipo_venta: 'texto', estado_cliente: 'texto',
  fecha_vencimiento_desde: 'fecha', fecha_vencimiento_hasta: 'fecha',
  fecha_emision_desde: 'fecha', fecha_emision_hasta: 'fecha',
}

const ORDEN_Y_ETIQUETAS_POR_DEFECTO = [
  { id: 'cliente', label: 'Cliente / RUC' },
  { id: 'ciudad', label: 'Ciudad' },
  { id: 'zona', label: 'Zona' },
  { id: 'sucursal', label: 'Sucursal' },
  { id: 'recuperador', label: 'Recuperador' },
  { id: 'causal', label: 'Causal' },
  { id: 'estado_cartera', label: 'Estado de cartera' },
  { id: 'rango_mora', label: 'Rango de mora' },
  { id: 'producto', label: 'Producto' },
  { id: 'articulo', label: 'Artículo' },
  { id: 'tipo_venta', label: 'Tipo de venta' },
  { id: 'estado_cliente', label: 'Estado del cliente' },
  { id: 'fecha_vencimiento_desde', label: 'Vencimiento desde' },
  { id: 'fecha_vencimiento_hasta', label: 'Vencimiento hasta' },
  { id: 'fecha_emision_desde', label: 'Emisión desde' },
  { id: 'fecha_emision_hasta', label: 'Emisión hasta' },
].map((f, i) => ({ ...f, order: i + 1, width: 2, is_visible: true }))

function CampoTexto({ label, campo, valor, onChange, width }) {
  return (
    <Col md={4} lg={width || 2}>
      <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>{label}</Form.Label>
      <Form.Control size="sm" value={valor} onChange={(e) => onChange(campo, e.target.value)} />
    </Col>
  )
}

function CampoSelect({ label, campo, valor, onChange, opciones, width }) {
  return (
    <Col md={4} lg={width || 2}>
      <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>{label}</Form.Label>
      <Form.Select size="sm" value={valor} onChange={(e) => onChange(campo, e.target.value)}>
        <option value="">Todos</option>
        {opciones.map((o) => <option key={o} value={o}>{o}</option>)}
      </Form.Select>
    </Col>
  )
}

function CampoFecha({ label, campo, valor, onChange, width }) {
  return (
    <Col md={4} lg={width || 2}>
      <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>{label}</Form.Label>
      <Form.Control type="date" size="sm" value={valor} onChange={(e) => onChange(campo, e.target.value)} />
    </Col>
  )
}

function renderCampo(definicion, filtros, onCambiarFiltro, opcionesRecuperador, opcionesCausal) {
  const tipo = TIPO_POR_CAMPO[definicion.id]
  const comunes = { key: definicion.id, label: definicion.label, campo: definicion.id, valor: filtros[definicion.id] || '', onChange: onCambiarFiltro, width: definicion.width }

  switch (tipo) {
    case 'fecha':
      return <CampoFecha {...comunes} />
    case 'select-recuperador':
      return <CampoSelect {...comunes} opciones={opcionesRecuperador} />
    case 'select-causal':
      return <CampoSelect {...comunes} opciones={opcionesCausal} />
    case 'select-estado-cartera':
      return <CampoSelect {...comunes} opciones={ESTADOS_CARTERA} />
    case 'select-rango-mora':
      return <CampoSelect {...comunes} opciones={RANGOS_MORA} />
    default:
      return <CampoTexto {...comunes} />
  }
}

/**
 * `configuracionFiltros` (opcional) viene de `panel-filtros.config.filtros` en el layout del
 * editor visual: orden, ancho, visibilidad, etiqueta y obligatoriedad de cada campo (sección
 * 12). Sin esa prop se usa el orden/etiquetas de siempre, así que el dashboard sin personalizar
 * se ve exactamente igual que antes.
 */
export default function FiltersPanel({
  filtros, onCambiarFiltro, onAplicar, onLimpiar, recuperadores, causales, resumenFiltrado,
  configuracionFiltros, override,
}) {
  const [expandido, setExpandido] = useState(true)
  const opcionesRecuperador = (recuperadores || []).map((r) => r.recuperador)
  const opcionesCausal = (causales?.causales || []).map((c) => c.causal)

  const definiciones = [...(configuracionFiltros || ORDEN_Y_ETIQUETAS_POR_DEFECTO)]
    .sort((a, b) => a.order - b.order)
    .filter((f) => f.is_visible)

  return (
    <div className="chart-panel mb-3">
      <div className="d-flex justify-content-between align-items-center">
        <div className="chart-panel__title mb-0">{override?.titulo || 'Filtros'}</div>
        <Button
          size="sm"
          variant="outline-secondary"
          onClick={() => setExpandido((v) => !v)}
          aria-expanded={expandido}
          aria-controls="panel-filtros-contenido"
        >
          {expandido ? 'Contraer ▲' : 'Expandir ▼'}
        </Button>
      </div>

      <Collapse in={expandido}>
        <div id="panel-filtros-contenido">
          <Row className="g-2 mb-2 mt-1">
            {definiciones.map((def) => renderCampo(def, filtros, onCambiarFiltro, opcionesRecuperador, opcionesCausal))}
          </Row>
          <div className="d-flex gap-2 mb-2">
            <Button size="sm" variant="primary" onClick={onAplicar}>Aplicar filtros</Button>
            <Button size="sm" variant="outline-secondary" onClick={onLimpiar}>Limpiar filtros</Button>
          </div>
        </div>
      </Collapse>

      {resumenFiltrado && (
        <div className="chart-panel__subtitle mb-0 mt-2">
          {formatNumber(resumenFiltrado.count)} registros visibles · Saldo filtrado: {formatCurrency(resumenFiltrado.saldo_filtrado)}
          {' '}({formatPercent(resumenFiltrado.porcentaje_sobre_cartera_total)} de la cartera total)
        </div>
      )}
    </div>
  )
}
