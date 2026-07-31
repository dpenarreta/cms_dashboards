import { useEffect, useState } from 'react'
import { Alert, Badge, Button, Form, Modal, Spinner, Table } from 'react-bootstrap'
import { useAuth } from '../../../context/AuthContext'
import * as auditService from '../../../services/auditService'

const DOMINIOS = [
  { value: '', label: 'Todos los dominios' },
  { value: 'SECURITY', label: 'Seguridad' },
  { value: 'AUTHENTICATION', label: 'Autenticación' },
  { value: 'USER_MANAGEMENT', label: 'Gestión de usuarios' },
  { value: 'ROLE_MANAGEMENT', label: 'Gestión de roles' },
  { value: 'PERMISSION_MANAGEMENT', label: 'Gestión de permisos' },
  { value: 'DASHBOARD_ACCESS', label: 'Acceso a dashboard' },
  { value: 'DASHBOARD_LAYOUT', label: 'Diseño de dashboard' },
  { value: 'DASHBOARD_CONFIGURATION', label: 'Configuración de dashboard' },
  { value: 'DATA_SOURCE', label: 'Fuente de datos' },
  { value: 'EXPORT', label: 'Exportación' },
  { value: 'FILE_UPLOAD', label: 'Carga de archivo' },
  { value: 'SYSTEM_CONFIGURATION', label: 'Configuración del sistema' },
]

const RESULTADOS = [
  { value: '', label: 'Todos los resultados' },
  { value: 'SUCCESS', label: 'Éxito' },
  { value: 'FAILED', label: 'Fallido' },
  { value: 'DENIED', label: 'Denegado' },
  { value: 'WARNING', label: 'Advertencia' },
]

const SEVERIDADES = [
  { value: '', label: 'Todas las severidades' },
  { value: 'INFO', label: 'Info' },
  { value: 'LOW', label: 'Baja' },
  { value: 'MEDIUM', label: 'Media' },
  { value: 'HIGH', label: 'Alta' },
  { value: 'CRITICAL', label: 'Crítica' },
]

const BADGE_RESULTADO = { SUCCESS: 'success', FAILED: 'danger', DENIED: 'danger', WARNING: 'warning' }
const BADGE_SEVERIDAD = { INFO: 'secondary', LOW: 'secondary', MEDIUM: 'warning', HIGH: 'danger', CRITICAL: 'danger' }

function formatFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-EC')
}

const FILTROS_INICIALES = {
  q: '', domain: '', action: '', result: '', severity: '', actor: '',
  dashboard_id: '', component_id: '', entity_type: '', ip_address: '', date_from: '', date_to: '',
}

export default function AuditListPage() {
  const { user } = useAuth()
  const puedeVerDetalle = user?.permissions?.includes('auditoria.ver_detalle')
  const puedeExportar = user?.permissions?.includes('auditoria.exportar')

  const [filtros, setFiltros] = useState(FILTROS_INICIALES)
  const [datos, setDatos] = useState({ results: [], count: 0, next: null, previous: null })
  const [pagina, setPagina] = useState(1)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  const [detalle, setDetalle] = useState(null)
  const [cargandoDetalle, setCargandoDetalle] = useState(false)
  const [errorDetalle, setErrorDetalle] = useState('')

  const [exportando, setExportando] = useState(false)

  const paramsActivos = () => {
    const params = { page: pagina }
    Object.entries(filtros).forEach(([clave, valor]) => {
      if (valor) params[clave] = valor
    })
    return params
  }

  const cargar = () => {
    setCargando(true)
    setError('')
    auditService.list(paramsActivos())
      .then(setDatos)
      .catch(() => setError('No se pudo cargar el historial de auditoría.'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [pagina]) // eslint-disable-line react-hooks/exhaustive-deps

  const aplicarFiltros = (e) => {
    e.preventDefault()
    setPagina(1)
    setCargando(true)
    setError('')
    auditService.list({ ...paramsActivos(), page: 1 })
      .then(setDatos)
      .catch(() => setError('No se pudo cargar el historial de auditoría.'))
      .finally(() => setCargando(false))
  }

  const limpiarFiltros = () => {
    setFiltros(FILTROS_INICIALES)
    setPagina(1)
  }

  const cambiarFiltro = (campo) => (e) => setFiltros((f) => ({ ...f, [campo]: e.target.value }))

  const verDetalle = (evento) => {
    setDetalle({ id: evento.id })
    setErrorDetalle('')
    setCargandoDetalle(true)
    auditService.get(evento.id)
      .then(setDetalle)
      .catch(() => setErrorDetalle('No se pudo cargar el detalle de este evento.'))
      .finally(() => setCargandoDetalle(false))
  }

  const exportar = async () => {
    setExportando(true)
    try {
      const blob = await auditService.exportCsv(paramsActivos())
      const url = URL.createObjectURL(blob)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = 'auditoria.csv'
      document.body.appendChild(enlace)
      enlace.click()
      enlace.remove()
      URL.revokeObjectURL(url)
    } catch {
      setError('No se pudo exportar el historial de auditoría.')
    } finally {
      setExportando(false)
    }
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <h1 className="h4 mb-0">Auditoría</h1>
        {puedeExportar && (
          <Button size="sm" variant="outline-secondary" disabled={exportando} onClick={exportar}>
            {exportando ? 'Exportando…' : 'Exportar CSV'}
          </Button>
        )}
      </div>

      <Form className="mb-3" onSubmit={aplicarFiltros}>
        <div className="d-flex gap-2 mb-2 flex-wrap">
          <Form.Control
            size="sm" style={{ maxWidth: 220 }} placeholder="Buscar (acción, mensaje, usuario)..."
            value={filtros.q} onChange={cambiarFiltro('q')}
          />
          <Form.Select size="sm" style={{ maxWidth: 200 }} value={filtros.domain} onChange={cambiarFiltro('domain')}>
            {DOMINIOS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
          </Form.Select>
          <Form.Select size="sm" style={{ maxWidth: 180 }} value={filtros.result} onChange={cambiarFiltro('result')}>
            {RESULTADOS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </Form.Select>
          <Form.Select size="sm" style={{ maxWidth: 180 }} value={filtros.severity} onChange={cambiarFiltro('severity')}>
            {SEVERIDADES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </Form.Select>
        </div>
        <div className="d-flex gap-2 mb-2 flex-wrap">
          <Form.Control size="sm" style={{ maxWidth: 160 }} placeholder="Acción" value={filtros.action} onChange={cambiarFiltro('action')} />
          <Form.Control size="sm" style={{ maxWidth: 160 }} placeholder="Usuario (id o nombre)" value={filtros.actor} onChange={cambiarFiltro('actor')} />
          <Form.Control size="sm" style={{ maxWidth: 140 }} placeholder="Dashboard" value={filtros.dashboard_id} onChange={cambiarFiltro('dashboard_id')} />
          <Form.Control size="sm" style={{ maxWidth: 140 }} placeholder="Componente" value={filtros.component_id} onChange={cambiarFiltro('component_id')} />
          <Form.Control size="sm" style={{ maxWidth: 140 }} placeholder="Tipo de entidad" value={filtros.entity_type} onChange={cambiarFiltro('entity_type')} />
          <Form.Control size="sm" style={{ maxWidth: 140 }} placeholder="Dirección IP" value={filtros.ip_address} onChange={cambiarFiltro('ip_address')} />
        </div>
        <div className="d-flex gap-2 align-items-center flex-wrap">
          <Form.Label className="mb-0" style={{ fontSize: '0.85rem' }}>Desde</Form.Label>
          <Form.Control size="sm" type="date" style={{ maxWidth: 170 }} value={filtros.date_from} onChange={cambiarFiltro('date_from')} />
          <Form.Label className="mb-0" style={{ fontSize: '0.85rem' }}>Hasta</Form.Label>
          <Form.Control size="sm" type="date" style={{ maxWidth: 170 }} value={filtros.date_to} onChange={cambiarFiltro('date_to')} />
          <Button size="sm" type="submit">Filtrar</Button>
          <Button size="sm" variant="outline-secondary" onClick={limpiarFiltros} type="button">Limpiar</Button>
        </div>
      </Form>

      {error && <Alert variant="danger">{error}</Alert>}
      {cargando && <div className="text-center py-3" role="status" aria-live="polite"><Spinner animation="border" size="sm" /></div>}

      {!cargando && (
        <div className="table-scroll">
          <Table size="sm" striped bordered hover>
            <thead>
              <tr>
                <th>Fecha y hora</th>
                <th>Dominio</th>
                <th>Acción</th>
                <th>Resultado</th>
                <th>Severidad</th>
                <th>Usuario</th>
                <th>Entidad</th>
                <th>Descripción</th>
                <th>IP</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {datos.results.map((e) => (
                <tr key={e.id}>
                  <td>{formatFecha(e.created_at)}</td>
                  <td>{DOMINIOS.find((d) => d.value === e.domain)?.label || e.domain}</td>
                  <td>{e.action}</td>
                  <td><Badge bg={BADGE_RESULTADO[e.result] || 'secondary'}>{e.result}</Badge></td>
                  <td><Badge bg={BADGE_SEVERIDAD[e.severity] || 'secondary'}>{e.severity}</Badge></td>
                  <td>{e.actor_username || '—'}</td>
                  <td>{[e.entity_type, e.entity_name || e.entity_id].filter(Boolean).join(': ') || '—'}</td>
                  <td>{e.message || '—'}</td>
                  <td>{e.ip_address || '—'}</td>
                  <td>
                    {puedeVerDetalle && (
                      <Button size="sm" variant="outline-secondary" onClick={() => verDetalle(e)}>Detalle</Button>
                    )}
                  </td>
                </tr>
              ))}
              {datos.results.length === 0 && (
                <tr><td colSpan={10} className="text-center text-secondary">No hay eventos que coincidan con los filtros.</td></tr>
              )}
            </tbody>
          </Table>
        </div>
      )}

      <div className="d-flex justify-content-between align-items-center">
        <div className="chart-panel__subtitle mb-0">{datos.count} evento(s)</div>
        <div className="d-flex gap-2">
          <Button size="sm" variant="outline-secondary" disabled={!datos.previous || cargando} onClick={() => setPagina((p) => p - 1)}>Anterior</Button>
          <Button size="sm" variant="outline-secondary" disabled={!datos.next || cargando} onClick={() => setPagina((p) => p + 1)}>Siguiente</Button>
        </div>
      </div>

      <Modal show={!!detalle} onHide={() => setDetalle(null)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Detalle del evento de auditoría</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {cargandoDetalle && <div className="text-center py-3"><Spinner animation="border" size="sm" /></div>}
          {errorDetalle && <Alert variant="danger">{errorDetalle}</Alert>}
          {!cargandoDetalle && detalle && detalle.action && (
            <>
              <dl className="row mb-3">
                <dt className="col-sm-3">Fecha y hora</dt><dd className="col-sm-9">{formatFecha(detalle.created_at)}</dd>
                <dt className="col-sm-3">Dominio</dt><dd className="col-sm-9">{detalle.domain}</dd>
                <dt className="col-sm-3">Acción</dt><dd className="col-sm-9">{detalle.action}</dd>
                <dt className="col-sm-3">Resultado</dt><dd className="col-sm-9">{detalle.result}</dd>
                <dt className="col-sm-3">Severidad</dt><dd className="col-sm-9">{detalle.severity}</dd>
                <dt className="col-sm-3">Usuario</dt><dd className="col-sm-9">{detalle.actor_username || '—'}</dd>
                <dt className="col-sm-3">Entidad</dt>
                <dd className="col-sm-9">{[detalle.entity_type, detalle.entity_name || detalle.entity_id].filter(Boolean).join(': ') || '—'}</dd>
                <dt className="col-sm-3">Dashboard / componente</dt>
                <dd className="col-sm-9">{[detalle.dashboard_id, detalle.component_id].filter(Boolean).join(' / ') || '—'}</dd>
                <dt className="col-sm-3">Dirección IP</dt><dd className="col-sm-9">{detalle.ip_address || '—'}</dd>
                <dt className="col-sm-3">Agente de usuario</dt><dd className="col-sm-9 text-break">{detalle.user_agent || '—'}</dd>
                <dt className="col-sm-3">Mensaje</dt><dd className="col-sm-9">{detalle.message || '—'}</dd>
              </dl>
              {'previous_values' in detalle && (
                <>
                  <h6>Valores anteriores</h6>
                  <pre className="bg-light p-2 border rounded" style={{ fontSize: '0.8rem', maxHeight: 200, overflow: 'auto' }}>
                    {JSON.stringify(detalle.previous_values, null, 2)}
                  </pre>
                  <h6>Valores nuevos</h6>
                  <pre className="bg-light p-2 border rounded" style={{ fontSize: '0.8rem', maxHeight: 200, overflow: 'auto' }}>
                    {JSON.stringify(detalle.new_values, null, 2)}
                  </pre>
                  <h6>Metadata</h6>
                  <pre className="bg-light p-2 border rounded" style={{ fontSize: '0.8rem', maxHeight: 200, overflow: 'auto' }}>
                    {JSON.stringify(detalle.metadata, null, 2)}
                  </pre>
                </>
              )}
            </>
          )}
        </Modal.Body>
      </Modal>
    </div>
  )
}
