import { useEffect, useState } from 'react'
import { Alert, Button, Form, Offcanvas } from 'react-bootstrap'
import WidthHeightControls from './WidthHeightControls'
import FilterFieldReorderList from './FilterFieldReorderList'

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/

const CAMPOS_COLOR = [
  { clave: 'colorPrincipal', etiqueta: 'Color principal' },
  { clave: 'colorVencido', etiqueta: 'Color de valores vencidos' },
  { clave: 'colorNoVencido', etiqueta: 'Color de valores no vencidos' },
  { clave: 'colorSinGestion', etiqueta: 'Color de categorías sin gestión' },
  { clave: 'colorTexto', etiqueta: 'Color del título' },
  { clave: 'colorFondo', etiqueta: 'Color de fondo' },
]

function CampoColor({ clave, etiqueta, valor, onCambiar }) {
  const [texto, setTexto] = useState(valor || '')
  const [errorLocal, setErrorLocal] = useState('')

  useEffect(() => setTexto(valor || ''), [valor])

  const aplicar = (nuevo) => {
    setTexto(nuevo)
    if (nuevo === '') {
      setErrorLocal('')
      onCambiar(clave, '')
      return
    }
    if (!HEX_RE.test(nuevo)) {
      setErrorLocal('Color inválido. Use formato hexadecimal, ej. #1F4E78.')
      return
    }
    setErrorLocal('')
    onCambiar(clave, nuevo)
  }

  return (
    <Form.Group className="mb-2">
      <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>{etiqueta}</Form.Label>
      <div className="d-flex gap-2 align-items-center">
        <Form.Control
          type="color"
          style={{ width: 44, padding: 2 }}
          value={HEX_RE.test(texto) ? texto : '#ffffff'}
          onChange={(e) => aplicar(e.target.value)}
          aria-label={`${etiqueta} (selector visual)`}
        />
        <Form.Control
          size="sm"
          value={texto}
          placeholder="#RRGGBB"
          onChange={(e) => aplicar(e.target.value)}
          aria-label={`${etiqueta} (hexadecimal)`}
        />
      </div>
      {errorLocal && <div className="text-danger" style={{ fontSize: '0.75rem' }}>{errorLocal}</div>}
    </Form.Group>
  )
}

export default function ComponentPropertiesPanel({
  componente, onCerrar, onActualizarContenido, onActualizarEstilos, onCambiarAncho, onCambiarAlto, onActualizarConfig,
}) {
  if (!componente) return null

  const restablecerColores = () => onActualizarEstilos(componente.component_id, Object.fromEntries(CAMPOS_COLOR.map((c) => [c.clave, ''])))

  return (
    <Offcanvas show={Boolean(componente)} onHide={onCerrar} placement="end" style={{ width: 380 }}>
      <Offcanvas.Header closeButton>
        <Offcanvas.Title>Configurar componente</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <Alert variant="secondary" className="py-2" style={{ fontSize: '0.8rem' }}>
          {componente.component_id}
        </Alert>

        <h6>Información general</h6>
        <Form.Group className="mb-2" controlId={`titulo-${componente.component_id}`}>
          <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>Título</Form.Label>
          <Form.Control
            size="sm"
            value={componente.content?.titulo || ''}
            onChange={(e) => onActualizarContenido(componente.component_id, { titulo: e.target.value })}
            maxLength={200}
          />
        </Form.Group>
        <Form.Group className="mb-3" controlId={`descripcion-${componente.component_id}`}>
          <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>Descripción</Form.Label>
          <Form.Control
            as="textarea"
            rows={2}
            size="sm"
            value={componente.content?.descripcion || ''}
            onChange={(e) => onActualizarContenido(componente.component_id, { descripcion: e.target.value })}
            maxLength={500}
          />
        </Form.Group>

        <h6>Tamaño</h6>
        <div className="mb-3">
          <WidthHeightControls
            width={componente.width}
            height={componente.height}
            onCambiarAncho={(w) => onCambiarAncho(componente.component_id, w)}
            onCambiarAlto={(h) => onCambiarAlto(componente.component_id, h)}
          />
        </div>

        <div className="d-flex justify-content-between align-items-center mb-2">
          <h6 className="mb-0">Colores</h6>
          <Button size="sm" variant="link" onClick={restablecerColores}>Restablecer colores</Button>
        </div>
        {CAMPOS_COLOR.map((c) => (
          <CampoColor
            key={c.clave}
            clave={c.clave}
            etiqueta={c.etiqueta}
            valor={componente.styles?.[c.clave]}
            onCambiar={(clave, valor) => onActualizarEstilos(componente.component_id, { [clave]: valor })}
          />
        ))}

        {componente.type === 'filters_panel' && componente.config?.filtros && (
          <>
            <h6>Orden de los filtros</h6>
            <FilterFieldReorderList
              filtros={componente.config.filtros}
              onCambiar={(nuevosFiltros) => onActualizarConfig(componente.component_id, { ...componente.config, filtros: nuevosFiltros })}
            />
          </>
        )}

        <Button variant="outline-secondary" size="sm" className="mt-2" onClick={onCerrar}>Cerrar</Button>
      </Offcanvas.Body>
    </Offcanvas>
  )
}
