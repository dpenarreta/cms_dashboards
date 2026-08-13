import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap'
import SettingsTabsBar from '../../../components/admin/SettingsTabsBar'
import * as brandingService from '../../../services/brandingService'
import { useTheme } from '../../../context/ThemeContext'
import { cumpleContrasteAA } from '../../../utils/colorContrast'

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/

// `contraClave` identifica el otro campo de color contra el que se compara el contraste real
// (el fondo o el texto con el que este color realmente aparece en pantalla) — comparar contra
// blanco/negro absolutos no sirve: todo color hex alcanza 4.5:1 contra al menos uno de los dos
// por construcción de la fórmula WCAG, así que esa comparación nunca advertiría nada.
const CAMPOS_COLOR = [
  { clave: 'color_primary', etiqueta: 'Color principal', contraClave: 'color_button_text' },
  { clave: 'color_secondary', etiqueta: 'Color secundario', contraClave: 'color_button_text' },
  { clave: 'color_background', etiqueta: 'Fondo de página' },
  { clave: 'color_headings', etiqueta: 'Títulos', contraClave: 'color_background' },
  { clave: 'color_text', etiqueta: 'Texto', contraClave: 'color_background' },
  { clave: 'color_links', etiqueta: 'Enlaces', contraClave: 'color_background' },
  { clave: 'color_buttons', etiqueta: 'Botones', contraClave: 'color_button_text' },
  { clave: 'color_menu', etiqueta: 'Menú' },
]

const CAMPOS_COLOR_SEMANTICOS = [
  { clave: 'color_success', etiqueta: 'Éxito', contraClave: 'color_button_text' },
  { clave: 'color_danger', etiqueta: 'Peligro', contraClave: 'color_button_text' },
  { clave: 'color_warning', etiqueta: 'Advertencia', contraClave: 'color_button_text' },
  { clave: 'color_info', etiqueta: 'Información', contraClave: 'color_button_text' },
  { clave: 'color_button_text', etiqueta: 'Texto de botones', contraClave: 'color_buttons' },
]

// Advertencia no bloqueante (WCAG AA, 4.5:1): se guarda igual si el usuario insiste, pero se
// muestra siempre antes — Módulo B, "trabajo futuro post-integración".
function AvisoContraste({ valor, contraValor }) {
  if (!HEX_RE.test(valor || '') || !HEX_RE.test(contraValor || '')) return null
  if (cumpleContrasteAA(valor, contraValor)) return null
  return (
    <div className="text-warning" style={{ fontSize: '0.75rem' }}>
      Contraste bajo frente a <code>{contraValor}</code>: puede ser difícil de leer.
    </div>
  )
}

/**
 * Vista previa en vivo de una fuente (principal o secundaria): texto de muestra renderizado con
 * el `font-family` real de la opción elegida (`fuente.css`, del catálogo — `opciones.fonts`,
 * `GET /api/branding/admin/options`). Se recalcula en cada render a partir del `<Form.Select>`
 * correspondiente (mismo estado `campos`, sin `useEffect` ni llamada aparte) — cambiar la
 * selección se ve reflejado al instante, sin necesidad de guardar. No toca `document.documentElement`
 * ni `ThemeContext` (eso solo se aplica recién tras guardar, vía `reloadTheme()`): es una muestra
 * aislada a este bloque, no una previsualización del resto de la página.
 */
function VistaPreviaFuente({ etiqueta, fuente }) {
  if (!fuente) return null
  return (
    <div className="border rounded p-2 mt-1" style={{ fontFamily: fuente.css }}>
      <div className="chart-panel__subtitle mb-1">Vista previa — {etiqueta}: {fuente.label}</div>
      <div style={{ fontSize: '1.05rem' }}>Aa Bb Cc 123 — El veloz murciélago hindú comía feliz cardillo y kiwi.</div>
    </div>
  )
}

function CampoColor({ clave, etiqueta, valor, contraValor, onCambiar }) {
  const valido = HEX_RE.test(valor || '')
  return (
    <Form.Group as={Col} md={6} className="mb-3" controlId={`settings-${clave}`}>
      <Form.Label style={{ fontSize: '0.85rem' }}>{etiqueta}</Form.Label>
      <div className="d-flex gap-2 align-items-center">
        <Form.Control
          type="color"
          style={{ width: 44, padding: 2 }}
          value={valido ? valor : '#ffffff'}
          onChange={(e) => onCambiar(clave, e.target.value)}
          aria-label={`${etiqueta} (selector visual)`}
        />
        <Form.Control size="sm" value={valor || ''} onChange={(e) => onCambiar(clave, e.target.value)} />
      </div>
      {!valido && valor && <div className="text-danger" style={{ fontSize: '0.75rem' }}>Color hexadecimal inválido.</div>}
      <AvisoContraste valor={valor} contraValor={contraValor} />
    </Form.Group>
  )
}

export default function SettingsPage() {
  const { reloadTheme } = useTheme()
  const [campos, setCampos] = useState(null)
  const [opciones, setOpciones] = useState({ fonts: [], border_radii: [] })
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  const cargar = () => {
    setCargando(true)
    Promise.all([brandingService.getAdmin(), brandingService.options()])
      .then(([tema, opts]) => {
        setCampos(tema)
        setOpciones(opts)
      })
      .catch(() => setError('No se pudo cargar la configuración institucional.'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [])

  const actualizarCampo = (clave, valor) => setCampos((prev) => ({ ...prev, [clave]: valor }))

  const guardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')
    setExito('')
    try {
      const tema = await brandingService.update(campos)
      setCampos(tema)
      reloadTheme()
      setExito('Configuración institucional guardada.')
    } catch (err) {
      setError(err.response?.data?.mensaje || 'No se pudo guardar la configuración.')
    } finally {
      setGuardando(false)
    }
  }

  const restablecer = async () => {
    if (!window.confirm('¿Restablecer la configuración institucional a sus valores por defecto?')) return
    setGuardando(true)
    setError('')
    try {
      const tema = await brandingService.reset()
      setCampos(tema)
      reloadTheme()
      setExito('Configuración restablecida a los valores por defecto.')
    } catch {
      setError('No se pudo restablecer la configuración.')
    } finally {
      setGuardando(false)
    }
  }

  if (cargando) return <div className="text-center py-4"><Spinner animation="border" /></div>
  if (!campos) return <Alert variant="danger">{error}</Alert>

  const fuentePrimaria = opciones.fonts.find((f) => f.slug === campos.font_primary)
  const fuenteSecundaria = opciones.fonts.find((f) => f.slug === campos.font_secondary)

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <h1 className="h4 mb-0">Configuración institucional</h1>
      </div>

      <SettingsTabsBar />

      {error && <Alert variant="danger">{error}</Alert>}
      {exito && <Alert variant="success">{exito}</Alert>}

      <Form onSubmit={guardar}>
        <Card className="chart-panel mb-3">
          <h6>Identidad</h6>
          <Row>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-site-name">
              <Form.Label>Nombre del sitio</Form.Label>
              <Form.Control value={campos.site_name} onChange={(e) => actualizarCampo('site_name', e.target.value)} required />
            </Form.Group>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-short-name">
              <Form.Label>Nombre corto</Form.Label>
              <Form.Control value={campos.short_name} onChange={(e) => actualizarCampo('short_name', e.target.value)} />
            </Form.Group>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-logo-url">
              <Form.Label>URL del logo</Form.Label>
              <Form.Control value={campos.logo_url} onChange={(e) => actualizarCampo('logo_url', e.target.value)} placeholder="https://..." />
            </Form.Group>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-favicon-url">
              <Form.Label>URL del favicon</Form.Label>
              <Form.Control value={campos.favicon_url} onChange={(e) => actualizarCampo('favicon_url', e.target.value)} placeholder="https://..." />
            </Form.Group>
          </Row>
        </Card>

        <Card className="chart-panel mb-3">
          <h6>Colores</h6>
          <Row>
            {CAMPOS_COLOR.map((c) => (
              <CampoColor
                key={c.clave} clave={c.clave} etiqueta={c.etiqueta} valor={campos[c.clave]}
                contraValor={c.contraClave ? campos[c.contraClave] : undefined}
                onCambiar={actualizarCampo}
              />
            ))}
          </Row>
        </Card>

        <Card className="chart-panel mb-3">
          <h6>Colores semánticos (Bootstrap)</h6>
          <p className="chart-panel__subtitle">
            Se conectan con las variables de Bootstrap (<code>--bs-success</code>, <code>--bs-danger</code>, etc.) que usan los
            componentes de la aplicación (alertas, badges, botones).
          </p>
          <Row>
            {CAMPOS_COLOR_SEMANTICOS.map((c) => (
              <CampoColor
                key={c.clave} clave={c.clave} etiqueta={c.etiqueta} valor={campos[c.clave]}
                contraValor={c.contraClave ? campos[c.contraClave] : undefined}
                onCambiar={actualizarCampo}
              />
            ))}
          </Row>
        </Card>

        <Card className="chart-panel mb-3">
          <h6>Tipografía y estilo</h6>
          <Row>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-font-primary">
              <Form.Label>Fuente principal</Form.Label>
              <Form.Select value={campos.font_primary} onChange={(e) => actualizarCampo('font_primary', e.target.value)}>
                {opciones.fonts.map((f) => <option key={f.slug} value={f.slug}>{f.label}</option>)}
              </Form.Select>
              <VistaPreviaFuente etiqueta="fuente principal" fuente={fuentePrimaria} />
            </Form.Group>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-font-secondary">
              <Form.Label>Fuente secundaria</Form.Label>
              <Form.Select value={campos.font_secondary} onChange={(e) => actualizarCampo('font_secondary', e.target.value)}>
                {opciones.fonts.map((f) => <option key={f.slug} value={f.slug}>{f.label}</option>)}
              </Form.Select>
              <VistaPreviaFuente etiqueta="fuente secundaria" fuente={fuenteSecundaria} />
            </Form.Group>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-font-size">
              <Form.Label>Tamaño de fuente base</Form.Label>
              <Form.Control value={campos.font_size_base} onChange={(e) => actualizarCampo('font_size_base', e.target.value)} placeholder="16px" />
            </Form.Group>
            <Form.Group as={Col} md={6} className="mb-2" controlId="settings-border-radius">
              <Form.Label>Radio de bordes</Form.Label>
              <Form.Select value={campos.border_radius} onChange={(e) => actualizarCampo('border_radius', e.target.value)}>
                {opciones.border_radii.map((r) => <option key={r.slug} value={r.slug}>{r.label}</option>)}
              </Form.Select>
            </Form.Group>
          </Row>
        </Card>

        <div className="d-flex gap-2">
          <Button type="submit" disabled={guardando}>{guardando ? <Spinner size="sm" animation="border" /> : 'Guardar cambios'}</Button>
          <Button type="button" variant="outline-secondary" disabled={guardando} onClick={restablecer}>Restablecer</Button>
        </div>
      </Form>
    </div>
  )
}
