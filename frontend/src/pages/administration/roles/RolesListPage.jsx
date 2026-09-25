import { useEffect, useState } from 'react'
import { Alert, Button, Spinner, Table } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import UsersRolesTabsBar from '../../../components/admin/UsersRolesTabsBar'
import ConfirmModal from '../../../components/dashboard-editor/ConfirmModal'
import * as rolesService from '../../../services/rolesService'

export default function RolesListPage() {
  const [datos, setDatos] = useState({ results: [], count: 0, next: null, previous: null })
  const [pagina, setPagina] = useState(1)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [rolAEliminar, setRolAEliminar] = useState(null)

  const cargar = () => {
    setCargando(true)
    setError('')
    rolesService.list({ page: pagina })
      .then(setDatos)
      .catch(() => setError('No se pudo cargar el listado de roles.'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [pagina]) // eslint-disable-line react-hooks/exhaustive-deps

  // Confirmación con `ConfirmModal` y no `window.confirm`: el diálogo nativo no es accesible ni
  // testeable, y la regla del repo (`.claude/rules/dashboards.md`) lo prohíbe explícitamente para
  // acciones destructivas — que es justo lo que es eliminar un rol.
  const eliminar = async () => {
    const rol = rolAEliminar
    setRolAEliminar(null)
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
          <Table responsive size="sm" striped bordered hover>
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
                    <Button size="sm" variant="outline-danger" onClick={() => setRolAEliminar(rol)}>Eliminar</Button>
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

      <ConfirmModal
        show={Boolean(rolAEliminar)}
        title="Eliminar rol"
        confirmLabel="Eliminar"
        onConfirm={eliminar}
        onCancel={() => setRolAEliminar(null)}
      >
        Se eliminará el rol <strong>{rolAEliminar?.name}</strong> y sus permisos dejarán de
        aplicarse a quienes lo tengan asignado. Esta acción no se puede deshacer.
      </ConfirmModal>
    </div>
  )
}
