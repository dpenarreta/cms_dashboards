import { useEffect, useState } from 'react'
import { Alert, Badge, Button, Form, Spinner, Table } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import * as usersService from '../../../services/usersService'

const ESTADOS = [
  { value: '', label: 'Todos los estados' },
  { value: 'active', label: 'Activo' },
  { value: 'disabled', label: 'Deshabilitado' },
  { value: 'blocked', label: 'Bloqueado' },
]

const ETIQUETA_ESTADO = { active: 'Activo', disabled: 'Deshabilitado', blocked: 'Bloqueado' }

export default function UsersListPage() {
  const [datos, setDatos] = useState({ results: [], count: 0, next: null, previous: null })
  const [pagina, setPagina] = useState(1)
  const [busqueda, setBusqueda] = useState('')
  const [estado, setEstado] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

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

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <h1 className="h4 mb-0">Usuarios</h1>
        <Button as={Link} to="/admin/users/new" size="sm">Nuevo usuario</Button>
      </div>

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
                  <td>
                    {u.status === 'active' ? (
                      <Button size="sm" variant="outline-secondary" onClick={() => cambiarEstado(u, 'disable')}>Deshabilitar</Button>
                    ) : (
                      <Button size="sm" variant="outline-secondary" onClick={() => cambiarEstado(u, 'enable')}>Habilitar</Button>
                    )}
                  </td>
                </tr>
              ))}
              {datos.results.length === 0 && (
                <tr><td colSpan={6} className="text-center text-secondary">No hay usuarios que coincidan con la búsqueda.</td></tr>
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
    </div>
  )
}
