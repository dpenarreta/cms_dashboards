import { Col, Row, Table } from 'react-bootstrap'
import { CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import GenericBarChart from './GenericBarChart'
import GenericStackedAreaChart from './GenericStackedAreaChart'
import GenericPieChart from './GenericPieChart'
import GenericScatterChart from './GenericScatterChart'
import { formatNumber } from '../../utils/format'

/**
 * Datos ficticios que ilustran las 9 formas de gráfica/tabla disponibles (barras, líneas, área
 * apilada, dona, pastel, dispersión, tablas) — no representan información real de ningún
 * dashboard. Se usan solo para la vista previa que se muestra al crear un dashboard, antes de
 * cargar el primer archivo.
 */
const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']

const KPIS = [
  { id: 'kpi1', etiqueta: 'KPI 1', valor: '12,458', variacion: '8.5%', color: '#2a78d6', icono: 'persona' },
  { id: 'kpi2', etiqueta: 'KPI 2', valor: '$1,245,300', variacion: '12.3%', color: '#1baf7a', icono: 'dolar' },
  { id: 'kpi3', etiqueta: 'KPI 3', valor: '3,682', variacion: '5.7%', color: '#8b5cf6', icono: 'carrito' },
  { id: 'kpi4', etiqueta: 'KPI 4', valor: '78.6%', variacion: '4.2%', color: '#eda100', icono: 'grafico' },
]

const GRAFICO_1 = { titulo: 'Gráfico 1', categorias: MESES, valores: [120000, 135000, 150000, 170000, 190000, 220000] }

const GRAFICO_2_DATOS = MESES.map((mes, i) => ({
  mes,
  'Ingresos (USD)': [110000, 130000, 160000, 180000, 210000, 240000][i],
  'Gastos (USD)': [70000, 80000, 90000, 110000, 120000, 140000][i],
}))

const GRAFICO_3 = {
  titulo: 'Gráfico 3',
  categorias: MESES,
  series: [
    { nombre: 'Producto A', valores: [60000, 65000, 70000, 75000, 80000, 100000] },
    { nombre: 'Producto B', valores: [50000, 55000, 60000, 60000, 65000, 80000] },
    { nombre: 'Producto C', valores: [40000, 45000, 50000, 45000, 55000, 60000] },
  ],
}

const CATEGORIAS_PRODUCTO_BASE = {
  categorias: ['Electrónica', 'Hogar', 'Moda', 'Deportes', 'Belleza'],
  valores: [245000, 180000, 135000, 98000, 87000],
}
// Gráfico 4 (dona, con total al centro) y Gráfico 5 (pastel) muestran la misma distribución de
// categorías — ver la imagen de referencia de la plantilla.
const GRAFICO_5 = { ...CATEGORIAS_PRODUCTO_BASE, titulo: 'Gráfico 5' }

const DISPERSION = {
  titulo: 'Gráfico 6',
  puntos: [
    { x: 60000, y: 8000 }, { x: 90000, y: 15000 }, { x: 110000, y: 22000 }, { x: 135000, y: 28000 },
    { x: 150000, y: 32000 }, { x: 180000, y: 45000 }, { x: 200000, y: 52000 }, { x: 220000, y: 60000 },
    { x: 245000, y: 70000 }, { x: 260000, y: 80000 },
  ],
}

const TABLA_PRODUCTOS = {
  columnas: ['Producto', 'Categoría', 'Ventas (USD)', 'Costo (USD)', 'Ganancia (USD)', 'Margen (%)', 'Unidades', 'Crecimiento vs. mes anterior'],
  filas: [
    ['Producto A', 'Electrónica', 245000, 150000, 95000, '38.8%', '1,250', 12.4],
    ['Producto B', 'Hogar', 180000, 110000, 70000, '38.9%', '980', 8.7],
    ['Producto C', 'Moda', 135000, 80000, 55000, '40.7%', '760', -3.2],
    ['Producto D', 'Deportes', 98000, 60000, 38000, '38.8%', '540', 6.1],
    ['Producto E', 'Belleza', 87000, 50000, 37000, '42.5%', '430', 9.3],
  ],
  total: ['Total', '', 745000, 450000, 295000, '39.6%', '3,960', 7.5],
}

const TABLA_REGIONES = {
  columnas: ['Región', 'Ventas (USD)', '% Participación', 'vs. mes anterior'],
  filas: [
    ['Norte', 230000, '30.9%', 9.8],
    ['Centro', 180000, '24.2%', 7.1],
    ['Sur', 165000, '22.1%', 5.4],
    ['Este', 120000, '16.1%', -1.8],
    ['Oeste', 50000, '6.7%', 3.6],
  ],
  total: ['Total', 745000, '100%', 7.5],
}

const TABLA_VENDEDORES = {
  columnas: ['Vendedor', 'Ventas (USD)', 'Unidades', 'Conversión (%)', 'vs. mes anterior'],
  filas: [
    ['María López', 145000, '780', '24.6%', 10.2],
    ['Juan Pérez', 130000, '650', '22.1%', 7.6],
    ['Ana Torres', 120000, '600', '21.3%', 6.3],
    ['Carlos Ruiz', 100000, '520', '19.8%', -2.4],
    ['Luis García', 85000, '410', '18.7%', 3.4],
  ],
  total: ['Total', 580000, '2,960', '21.3%', 5.8],
}

const COLORES_LINEA = ['#2a78d6', '#1baf7a']

function IconoIndicador({ tipo }) {
  const trazos = {
    persona: <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>,
    dolar: <><line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></>,
    carrito: <><circle cx="9" cy="21" r="1" /><circle cx="20" cy="21" r="1" /><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" /></>,
    grafico: <><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></>,
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {trazos[tipo]}
    </svg>
  )
}

function TarjetaKpiIlustrativa({ kpi }) {
  return (
    <div className="kpi-card" style={{ borderLeft: `4px solid ${kpi.color}` }}>
      <div className="d-flex align-items-center gap-2 mb-2">
        <div
          className="d-flex align-items-center justify-content-center rounded-circle"
          style={{ width: 34, height: 34, background: `${kpi.color}22`, color: kpi.color, flexShrink: 0 }}
        >
          <IconoIndicador tipo={kpi.icono} />
        </div>
        <div className="kpi-card__label mb-0">{kpi.etiqueta}</div>
      </div>
      <div className="kpi-card__value">{kpi.valor}</div>
      <div className="kpi-card__sub" style={{ color: 'var(--status-good)' }}>
        ↑ {kpi.variacion} vs. mes anterior
      </div>
    </div>
  )
}

function GraficoDosLineasIlustrativo() {
  return (
    <div className="chart-panel">
      <div className="chart-panel__title">Gráfico 2</div>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={GRAFICO_2_DATOS} margin={{ left: 8, right: 24, bottom: 8 }}>
          <CartesianGrid stroke="var(--gridline)" />
          <XAxis dataKey="mes" />
          <YAxis tickFormatter={(v) => formatNumber(v)} />
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend />
          <Line type="monotone" dataKey="Ingresos (USD)" stroke={COLORES_LINEA[0]} strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Gastos (USD)" stroke={COLORES_LINEA[1]} strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function GraficoDonaConTotalIlustrativo() {
  const total = CATEGORIAS_PRODUCTO_BASE.valores.reduce((suma, v) => suma + v, 0)
  return (
    <div className="chart-panel" style={{ position: 'relative' }}>
      <div className="chart-panel__title">Gráfico 4</div>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={CATEGORIAS_PRODUCTO_BASE.categorias.map((c, i) => ({ nombre: c, valor: CATEGORIAS_PRODUCTO_BASE.valores[i] }))}
            dataKey="valor"
            nameKey="nombre"
            innerRadius="55%"
            outerRadius="80%"
            paddingAngle={2}
          >
            {CATEGORIAS_PRODUCTO_BASE.categorias.map((c, i) => (
              <Cell key={c} fill={`var(--series-${(i % 8) + 1})`} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatNumber(value)} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
      <div
        className="text-center"
        style={{ position: 'absolute', top: '46%', left: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none' }}
      >
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Total</div>
        <div style={{ fontWeight: 600 }}>{formatNumber(total)}</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>USD</div>
      </div>
    </div>
  )
}

function celdaCrecimiento(valor) {
  const positivo = valor >= 0
  return (
    <span style={{ color: positivo ? 'var(--status-good)' : 'var(--status-critical)' }}>
      {positivo ? '↑' : '↓'} {Math.abs(valor).toFixed(1)}%
    </span>
  )
}

function TablaIlustrativa({ columnas, filas, total }) {
  return (
    <Table responsive size="sm" className="mb-0">
      <thead>
        <tr>
          {columnas.map((c) => <th key={c} className={typeof filas[0]?.[columnas.indexOf(c)] === 'number' ? 'text-end' : undefined}>{c}</th>)}
        </tr>
      </thead>
      <tbody>
        {filas.map((fila, i) => (
          // eslint-disable-next-line react/no-array-index-key
          <tr key={i}>
            {fila.map((valor, j) => {
              const esUltima = j === fila.length - 1
              return (
                <td key={columnas[j]} className={typeof valor === 'number' && !esUltima ? 'text-end' : (esUltima ? 'text-end' : undefined)}>
                  {esUltima && typeof valor === 'number' ? celdaCrecimiento(valor) : (typeof valor === 'number' ? formatNumber(valor) : valor)}
                </td>
              )
            })}
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr className="fw-bold">
          {total.map((valor, j) => {
            const esUltima = j === total.length - 1
            return (
              <td key={columnas[j]} className={typeof valor === 'number' && !esUltima ? 'text-end' : (esUltima ? 'text-end' : undefined)}>
                {esUltima && typeof valor === 'number' ? celdaCrecimiento(valor) : (typeof valor === 'number' ? formatNumber(valor) : valor)}
              </td>
            )
          })}
        </tr>
      </tfoot>
    </Table>
  )
}

/**
 * Vista previa ilustrativa de un dashboard terminado — se muestra al crear un dashboard nuevo,
 * antes de cargar cualquier archivo, para que el usuario vea de entrada qué formas de KPI/gráfica
 * /tabla puede llegar a construir. Todos los datos son ficticios (no se guardan ni se envían al
 * backend); en cuanto el usuario carga un archivo real, el flujo de recomendaciones
 * (`ChartRecommendations`) reemplaza esta vista con gráficas armadas a partir de sus propios
 * datos. Reutiliza los componentes `Generic*` donde la forma del dato coincide 1:1 (barras de una
 * serie, área apilada, dispersión, pastel) para no duplicar esa lógica de renderizado; el resto
 * (comparación de dos líneas, dona con total al centro, tablas con más de dos columnas) no tiene
 * un componente genérico equivalente todavía, así que se arma aquí mismo.
 */
export default function DashboardPlaceholderTemplate() {
  return (
    <div aria-label="Vista previa ilustrativa de un dashboard" style={{ opacity: 0.96 }}>
      <div className="mb-3">
        <h2 className="mb-1">Título del Dashboard</h2>
        <p className="chart-panel__subtitle mb-1" style={{ fontSize: '1rem' }}>Subtítulo (Área)</p>
        <p className="chart-panel__subtitle mb-0">Detalle o descripción</p>
      </div>

      <Row className="g-3 mb-3">
        {KPIS.map((kpi) => (
          <Col key={kpi.id} md={6} lg={3}><TarjetaKpiIlustrativa kpi={kpi} /></Col>
        ))}
      </Row>

      <Row className="g-3 mb-3">
        <Col md={6}><GenericBarChart data={GRAFICO_1} orientacion="vertical" /></Col>
        <Col md={6}><GraficoDosLineasIlustrativo /></Col>
      </Row>

      <Row className="g-3 mb-3">
        <Col xs={12}><GenericStackedAreaChart data={GRAFICO_3} /></Col>
      </Row>

      <Row className="g-3 mb-3">
        <Col xs={12}>
          <div className="chart-panel">
            <div className="chart-panel__title">Tabla 1</div>
            <TablaIlustrativa {...TABLA_PRODUCTOS} />
          </div>
        </Col>
      </Row>

      <Row className="g-3 mb-3">
        <Col md={4}><GraficoDonaConTotalIlustrativo /></Col>
        <Col md={4}><GenericPieChart data={GRAFICO_5} /></Col>
        <Col md={4}><GenericScatterChart data={DISPERSION} /></Col>
      </Row>

      <Row className="g-3">
        <Col md={6}>
          <div className="chart-panel">
            <div className="chart-panel__title">Tabla 2</div>
            <TablaIlustrativa {...TABLA_REGIONES} />
          </div>
        </Col>
        <Col md={6}>
          <div className="chart-panel">
            <div className="chart-panel__title">Tabla 3</div>
            <TablaIlustrativa {...TABLA_VENDEDORES} />
          </div>
        </Col>
      </Row>
    </div>
  )
}
