import { useDraggable } from '@dnd-kit/core'
import { Offcanvas } from 'react-bootstrap'

/** Cada tarjeta es tanto arrastrable (`useDraggable`, soltar sobre `zona-personal-drop` en
 * `DashboardAreaPage.jsx`) como clicable (alternativa sin arrastre, misma acción resultante) —
 * `id` es el prefijo `paleta-<tipo>` que `DashboardAreaPage.jsx::manejarElegirTipo` reconoce en
 * `onDragEnd`. Los tipos con datos reales (`kpi`/`chart`/`multivalor`/`multiserie`/`tabla`/
 * `dispersion`) abren `AgregarComponentePersonalModal` para elegir columnas antes de crear el
 * componente; `separador`/`titulo` (sin datos) se crean de inmediato. */
const TARJETAS = [
  { tipo: 'separador', etiqueta: 'Separador', descripcion: 'Línea divisoria', icono: '—' },
  { tipo: 'titulo', etiqueta: 'Título', descripcion: 'Bloque de encabezado', icono: 'T' },
  { tipo: 'kpi', etiqueta: 'Tarjeta KPI', descripcion: 'Un solo valor', icono: '#' },
  { tipo: 'chart', etiqueta: 'Gráfico', descripcion: 'Datos por columna', icono: '📊' },
  { tipo: 'tabla', etiqueta: 'Tabla', descripcion: 'Detalle por filas', icono: '▦' },
]

function TarjetaComponente({ tipo, etiqueta, descripcion, icono, onElegirTipo }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: `paleta-${tipo}` })
  return (
    <button
      type="button"
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      onClick={() => onElegirTipo(tipo)}
      className="d-flex align-items-center gap-2 w-100 text-start mb-2 p-2 border rounded bg-body"
      style={{ cursor: 'grab', opacity: isDragging ? 0.4 : 1 }}
    >
      <span aria-hidden="true" style={{ fontSize: '1.1rem', width: 24, textAlign: 'center' }}>{icono}</span>
      <span>
        <div className="fw-semibold" style={{ fontSize: '0.9rem' }}>{etiqueta}</div>
        <div className="chart-panel__subtitle mb-0" style={{ fontSize: '0.75rem' }}>{descripcion}</div>
      </span>
    </button>
  )
}

/**
 * Panel lateral derecho del editor de dashboard (sección "panel de componentes"): paleta de
 * tipos de componente arrastrables hacia la Zona Personal (`ZonaPersonalDropTarget`, en
 * `DashboardAreaPage.jsx`) — se abre solo al entrar en modo edición. `Offcanvas` con
 * `backdrop={false}` para no bloquear el lienzo mientras está abierto (a diferencia de
 * `ComponentPropertiesPanel`, que sí es un overlay modal clásico).
 */
export default function ComponentPaletteSidebar({ show, onHide, onElegirTipo }) {
  return (
    <Offcanvas show={show} onHide={onHide} placement="end" backdrop={false} scroll style={{ width: 260, top: 'auto' }}>
      <Offcanvas.Header closeButton>
        <Offcanvas.Title style={{ fontSize: '1rem' }}>Componentes</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <p className="chart-panel__subtitle" style={{ fontSize: '0.8rem' }}>
          Arrastrá un componente hasta la Zona Personal, o hacé clic para elegirlo.
        </p>
        {TARJETAS.map((t) => <TarjetaComponente key={t.tipo} {...t} onElegirTipo={onElegirTipo} />)}
      </Offcanvas.Body>
    </Offcanvas>
  )
}
