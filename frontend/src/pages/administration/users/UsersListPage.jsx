import { useEffect, useState } from 'react'
import { Alert, Badge, Button, Form, Modal, Spinner, Table } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import ConfirmModal from '../../../components/dashboard-editor/ConfirmModal'
import UsersRolesTabsBar from '../../../components/admin/UsersRolesTabsBar'
import { useAuth } from '../../../context/AuthContext'
import * as usersService from '../../../services/usersService'

const ESTADOS = [
  { value: '', label: 'Todos los estados' },
  { value: 'active', label: 'Activo' },
  { value: 'disabled', label: 'Deshabilitado' },
  { value: 'blocked', label: 'Bloqueado' },
]

const ETIQUETA_ESTADO = { active: 'Activo', disabled: 'Deshabilitado', blocked: 'Bloqueado' }

// Mismo patrón que `AuditListPage.jsx::formatFecha` — sin formateador de fecha+hora compartido
// en `utils/format.js` (ese solo tiene `formatDate`, sin hora).
function formatFecha(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('es-EC')
}

export default function UsersListPage() {
  const { user } = useAuth()
  const puedeRestablecerPassword = Boolean(user?.permissions?.includes('usuarios.restablecer_password'))

  const [datos, setDatos] = useState({ results: [], count: 0, next: null, previous: null })
  const [pagina, setPagina] = useState(1)
  const [busqueda, setBusqueda] = useState('')
  const [estado, setEstado] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  const [usuarioARestablecer, setUsuarioARestablecer] = useState(null)
  const [restableciendo, setRestableciendo] = useState(false)
  const [passwordGenerada, setPasswordGenerada] = useState(null)

  const cargar = () => {
    setCargando(true)
    setError('')
    usersService.list({ page: pagina, q: busqueda || undefined, status: estado || undefined })
      .then(setDatos)
      .catch(() => setError('No se pudo cargar el listado de usuarios.'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [pagina, busqueda, estado]) // eslint-disable-line react-hooks/exhaustive-deps

  const cambiarEstado = async (usuario, accion) => {
    setError('')
    try {
      await usersService[accion](usuario.id)
      cargar()
    } catch {
      setError(`No se pudo ${accion === 'enable' ? 'habilitar' : 'deshabilitar'} el usuario.`)
    }
  }

  const confirmarRestablecerPassword = async () => {
    setRestableciendo(true)
    setError('')
    try {
      const resultado = await usersService.resetPassword(usuarioARestablecer.id)
      setPasswordGenerada({ username: usuarioARestablecer.username, password: resultado.temporary_password })
      setUsuarioARestablecer(null)
      cargar()
    } catch {
      setError('No se pudo restablecer la contraseña del usuario.')
      setUsuarioARestablecer(null)
    } finally {
      setRestableciendo(false)
    }
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <h1 className="h4 mb-0">Usuarios</h1>
        <Button as={Link} to="/admin/users/new" size="sm">Nuevo usuario</Button>
      </div>

      <UsersRolesTabsBar />

      <div className="d-flex gap-2 mb-3 flex-wrap">
        <Form.Control
          size="sm"
          style={{ maxWidth: 260 }}
          placeholder="Buscar por usuario, correo o nombre..."
          value={busqueda}
          onChange={(e) => { setPagina(1); setBusqueda(e.target.value) }}
        />
        <Form.Select size="sm" style={{ maxWidth: 200 }} value={estado} onChange={(e) => { setPagina(1); setEstado(e.target.value) }}>
          {ESTADOS.map((e) => <option key={e.value} value={e.value}>{e.label}</option>)}
        </Form.Select>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {cargando && <div className="text-center py-3" role="status" aria-live="polite"><Spinner animation="border" size="sm" /></div>}

      {!cargando && (
        <div className="table-scroll">
          <Table size="sm" striped bordered hover>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Correo</th>
                <th>Nombre</th>
                <th>Estado</th>
                <th>Roles</th>
                <th>Última conexión</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {datos.results.map((u) => (
                <tr key={u.id}>
                  <td>
                    <Link to={`/admin/users/${u.id}`}>{u.username}</Link>
                    {u.is_superuser && <Badge bg="dark" className="ms-2">Superusuario</Badge>}
                  </td>
                  <td>{u.email}</td>
                  <td>{[u.first_name, u.last_name].filter(Boolean).join(' ') || '—'}</td>
                  <td>{ETIQUETA_ESTADO[u.status] || u.status}</td>
                  <td>{u.roles.join(', ') || '—'}</td>
                  <td>{formatFecha(u.ultima_conexion)}</td>
                  <td>
                    <div className="d-flex gap-2 flex-wrap">
                      {u.status === 'active' ? (
                        <Button size="sm" variant="outline-secondary" onClick={() => cambiarEstado(u, 'disable')}>Deshabilitar</Button>
                      ) : (
                        <Button size="sm" variant="outline-secondary" onClick={() => cambiarEstado(u, 'enable')}>Habilitar</Button>
                      )}
                      {puedeRestablecerPassword && (
                        <Button size="sm" variant="outline-warning" onClick={() => setUsuarioARestablecer(u)}>Restablecer contraseña</Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {datos.results.length === 0 && (
                <tr><td colSpan={7} className="text-center text-secondary">No hay usuarios que coincidan con la búsqueda.</td></tr>
              )}
            </tbody>
          </Table>
        </div>
      )}

      <div className="d-flex justify-content-between align-items-center">
        <div className="chart-panel__subtitle mb-0">{datos.count} usuario(s)</div>
        <div className="d-flex gap-2">
          <Button size="sm" variant="outline-secondary" disabled={!datos.previous || cargando} onClick={() => setPagina((p) => p - 1)}>Anterior</Button>
          <Button size="sm" variant="outline-secondary" disabled={!datos.next || cargando} onClick={() => setPagina((p) => p + 1)}>Siguiente</Button>
        </div>
      </div>

      <ConfirmModal
        show={Boolean(usuarioARestablecer)}
        title="Restablecer contraseña"
        onCancel={() => setUsuarioARestablecer(null)}
        onConfirm={confirmarRestablecerPassword}
        confirmLabel={restableciendo ? 'Restableciendo...' : 'Restablecer'}
        confirmVariant="warning"
      >
        {usuarioARestablecer && (
          <>
            Se generará una nueva contraseña temporal para <strong>{usuarioARestablecer.username}</strong>,
            se cerrarán todas sus sesiones activas y deberá cambiarla en su próximo inicio de sesión.
            ¿Deseas continuar?
          </>
        )}
      </ConfirmModal>

      <Modal show={Boolean(passwordGenerada)} onHide={() => setPasswordGenerada(null)} centered>
        <Modal.Header closeButton>
          <Modal.Title>Contraseña restablecida</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {passwordGenerada && (
            <>
              <p>
                Contraseña temporal para <strong>{passwordGenerada.username}</strong> — compártela
                de forma segura, no se mostrará de nuevo:
              </p>
              <div className="d-flex gap-2">
                <Form.Control readOnly value={passwordGenerada.password} onFocus={(e) => e.target.select()} />
                <Button
                  variant="outline-secondary"
                  onClick={() => navigator.clipboard?.writeText(passwordGenerada.password)}
                >
                  Copiar
                </Button>
              </div>
            </>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setPasswordGenerada(null)}>Cerrar</Button>
        </Modal.Footer>
      </Modal>
    </div>
  )
}
