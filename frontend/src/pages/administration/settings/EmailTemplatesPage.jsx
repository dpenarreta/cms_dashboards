import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Form, Row, Spinner } from 'react-bootstrap'
import ReactQuill from 'react-quill-new'
import 'react-quill-new/dist/quill.snow.css'
import '../../../styles/emailTemplates.css'
import ConfirmModal from '../../../components/dashboard-editor/ConfirmModal'
import SettingsTabsBar from '../../../components/admin/SettingsTabsBar'
import * as emailTemplatesService from '../../../services/emailTemplatesService'

// Hoy solo hay una plantilla de correo en todo el sistema (recuperación de contraseña) — ver
// `backend/apps/authentication/models.py::EmailTemplate.KEY_CHOICES`. El resto de esta página ya
// está armado para más de una (`key` como parámetro, no hardcodeado en el cuerpo del componente).
const PLANTILLA_KEY = 'password_reset'

const OPCIONES_EDITOR = {
  toolbar: [
    [{ header: [1, 2, 3, false] }],
    ['bold', 'italic', 'underline'],
    [{ color: [] }, { background: [] }],
    [{ align: [] }],
    [{ list: 'ordered' }, { list: 'bullet' }],
    ['link'],
    ['clean'],
  ],
}

// Valores de ejemplo solo para la vista previa (nunca se mandan al backend) — mismos nombres de
// variable que ya resuelve el backend en `services.py::_enviar_correo_recuperacion`.
const CONTEXTO_DE_MUESTRA = {
  nombre_usuario: 'Ana Torres',
  enlace: 'https://tu-dominio.com/reset-password?token=ejemplo-de-token',
  minutos_expiracion: '30',
  site_name: 'Dashboard de Cartera',
  color_primary: '#2a78d6',
}

// `(?:\s|&nbsp;)*`, no solo `\s*`: Quill reescribe el HTML al guardar y convierte espacios
// normales en la entidad literal `&nbsp;` (comportamiento normal de un contenteditable, para que
// el navegador no los colapse visualmente) — pasa sobre todo justo alrededor de `{{`/`}}`. Mismo
// ajuste que `backend/apps/authentication/services.py::_MARCADOR_RE`.
const MARCADOR_RE = /\{\{(?:\s|&nbsp;)*(\w+)(?:\s|&nbsp;)*\}\}/g

function sustituirVariables(texto, contexto) {
  return (texto || '').replace(MARCADOR_RE, (coincidencia, clave) => (
    Object.prototype.hasOwnProperty.call(contexto, clave) ? contexto[clave] : coincidencia
  ))
}

/**
 * Editor de la plantilla de correo de recuperación de contraseña: asunto + HTML propio con un
 * editor de texto enriquecido (`react-quill-new`) en vez de HTML a mano. El HTML se guarda tal
 * cual lo entrega el editor — la sustitución real de `{{ variable }}` (con escape de los valores
 * insertados) vive en el backend (`services.py::_renderizar_plantilla`); acá la vista previa hace
 * la misma sustitución con datos de ejemplo, puramente en el cliente, para "ver cómo quedaría"
 * sin tener que guardar ni mandar un correo de prueba.
 *
 * La vista previa se renderiza en un `<iframe sandbox="">` (sin `allow-scripts`) a propósito: es
 * HTML compuesto por un editor WYSIWYG, no texto de por sí confiable para inyectar en la página
 * tal cual — el sandbox vacío neutraliza cualquier `<script>` que pudiera colarse, sea por un
 * pegado descuidado en el editor o por manipulación directa del campo vía la API.
 */
export default function EmailTemplatesPage() {
  const [subject, setSubject] = useState('')
  const [htmlBody, setHtmlBody] = useState('')
  const [variables, setVariables] = useState([])
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [restableciendo, setRestableciendo] = useState(false)
  const [mostrarConfirmarReset, setMostrarConfirmarReset] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  const cargar = () => {
    setCargando(true)
    setError('')
    emailTemplatesService.get(PLANTILLA_KEY)
      .then((plantilla) => {
        setSubject(plantilla.subject)
        setHtmlBody(plantilla.html_body)
        setVariables(plantilla.variables || [])
      })
      .catch(() => setError('No se pudo cargar la plantilla de correo.'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [])

  const guardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')
    setExito('')
    try {
      const plantilla = await emailTemplatesService.update(PLANTILLA_KEY, { subject, htmlBody })
      setSubject(plantilla.subject)
      setHtmlBody(plantilla.html_body)
      setExito('Plantilla de correo guardada.')
    } catch (err) {
      setError(err.response?.data?.mensaje || 'No se pudo guardar la plantilla de correo.')
    } finally {
      setGuardando(false)
    }
  }

  const confirmarRestablecer = async () => {
    setMostrarConfirmarReset(false)
    setRestableciendo(true)
    setError('')
    setExito('')
    try {
      const plantilla = await emailTemplatesService.reset(PLANTILLA_KEY)
      setSubject(plantilla.subject)
      setHtmlBody(plantilla.html_body)
      setExito('Plantilla restablecida al contenido por defecto.')
    } catch {
      setError('No se pudo restablecer la plantilla de correo.')
    } finally {
      setRestableciendo(false)
    }
  }

  const asuntoPreview = useMemo(() => sustituirVariables(subject, CONTEXTO_DE_MUESTRA), [subject])
  const htmlPreview = useMemo(() => sustituirVariables(htmlBody, CONTEXTO_DE_MUESTRA), [htmlBody])

  if (cargando) return <div className="text-center py-4"><Spinner animation="border" /></div>

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <h1 className="h4 mb-0">Plantilla de correo: recuperación de contraseña</h1>
      </div>

      <SettingsTabsBar />

      {error && <Alert variant="danger">{error}</Alert>}
      {exito && <Alert variant="success">{exito}</Alert>}

      {variables.length > 0 && (
        <Alert variant="secondary" className="mb-3">
          <div className="fw-semibold mb-1">Variables disponibles</div>
          <div className="d-flex flex-column gap-1" style={{ fontSize: '0.85rem' }}>
            {variables.map((v) => (
              <div key={v.name}><code>{`{{ ${v.name} }}`}</code> — {v.description}</div>
            ))}
          </div>
        </Alert>
      )}

      <Form onSubmit={guardar}>
        <Row className="g-3">
          <Col lg={7}>
            <Card className="chart-panel mb-3">
              <Form.Group className="mb-3" controlId="email-template-subject">
                <Form.Label>Asunto</Form.Label>
                <Form.Control value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={200} required />
              </Form.Group>
              <Form.Group controlId="email-template-body">
                <Form.Label>Cuerpo del correo</Form.Label>
                <ReactQuill theme="snow" value={htmlBody} onChange={setHtmlBody} modules={OPCIONES_EDITOR} />
              </Form.Group>
            </Card>

            <div className="d-flex gap-2">
              <Button type="submit" disabled={guardando || restableciendo}>
                {guardando ? <Spinner size="sm" animation="border" /> : 'Guardar cambios'}
              </Button>
              <Button
                type="button" variant="outline-secondary" disabled={guardando || restableciendo}
                onClick={() => setMostrarConfirmarReset(true)}
              >
                Restablecer al contenido por defecto
              </Button>
            </div>
          </Col>

          <Col lg={5}>
            <Card className="chart-panel">
              <div className="fw-semibold mb-2">Vista previa (con datos de ejemplo)</div>
              <div className="chart-panel__subtitle mb-2">Asunto: {asuntoPreview}</div>
              <iframe
                title="Vista previa del correo"
                srcDoc={htmlPreview}
                sandbox=""
                style={{ width: '100%', minHeight: 420, border: '1px solid var(--border)', borderRadius: 8, background: '#fff' }}
              />
            </Card>
          </Col>
        </Row>
      </Form>

      <ConfirmModal
        show={mostrarConfirmarReset}
        title="Restablecer plantilla de correo"
        onCancel={() => setMostrarConfirmarReset(false)}
        onConfirm={confirmarRestablecer}
        confirmLabel="Restablecer"
        confirmVariant="warning"
      >
        Se reemplazará el asunto y el HTML actuales por el contenido por defecto. Los cambios que
        hayas guardado se perderán. ¿Deseas continuar?
      </ConfirmModal>
    </div>
  )
}
