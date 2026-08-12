import { useEffect, useState } from 'react'
import { Alert, Button, Spinner, Table } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import UsersRolesTabsBar from '../../../components/admin/UsersRolesTabsBar'
import * as rolesService from '../../../services/rolesService'

export default function RolesListPage() {
  const [datos, setDatos] = useState({ results: [], count: 0, next: null, previous: null })
  const [pagina, setPagina] = useState(1)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')

  const cargar = () => {
    setCargando(true)
    setError('')
    rolesService.list({ page: pagina })
      .then(setDatos)
      .catch(() => setError('No se pudo cargar el listado de roles.'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [pagina]) // eslint-disable-line react-hooks/exhaustive-deps

  const eliminar = async (rol) => {
    if (!window.confirm(`¿Eliminar el rol "${rol.name}"? Esta acción no se puede deshacer.`)) return
    setError('')
    try {
      await rolesService.remove(rol.id)
      cargar()
    } catch {
      setError('No se pudo eliminar el rol.')
    }
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <h1 className="h4 mb-0">Roles</h1>
        <Button as={Link} to="/admin/roles/new" size="sm">Nuevo rol</Button>
      </div>

      <UsersRolesTabsBar />

      {error && <Alert variant="danger">{error}</Alert>}
      {cargando && <div className="text-center py-3" role="status" aria-live="polite"><Spinner animation="border" size="sm" /></div>}

      {!cargando && (
        <div className="table-scroll">
          <Table size="sm" striped bordered hover>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Permisos asignados</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {datos.results.map((rol) => (
                <tr key={rol.id}>
                  <td><Link to={`/admin/roles/${rol.id}`}>{rol.name}</Link></td>
                  <td>{rol.permission_codenames.length}</td>
                  <td>
                    <Button size="sm" variant="outline-danger" onClick={() => eliminar(rol)}>Eliminar</Button>
                  </td>
                </tr>
              ))}
              {datos.results.length === 0 && (
                <tr><td colSpan={3} className="text-center text-secondary">No hay roles creados todavía.</td></tr>
              )}
            </tbody>
          </Table>
        </div>
      )}

      <div className="d-flex justify-content-between align-items-center">
        <div className="chart-panel__subtitle mb-0">{datos.count} rol(es)</div>
        <div className="d-flex gap-2">
          <Button size="sm" variant="outline-secondary" disabled={!datos.previous || cargando} onClick={() => setPagina((p) => p - 1)}>Anterior</Button>
          <Button size="sm" variant="outline-secondary" disabled={!datos.next || cargando} onClick={() => setPagina((p) => p + 1)}>Siguiente</Button>
        </div>
      </div>
    </div>
  )
}
