import { useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Spinner } from 'react-bootstrap'
import { useNavigate, useParams } from 'react-router-dom'
import * as permissionsService from '../../../services/permissionsService'
import * as rolesService from '../../../services/rolesService'
import * as usersService from '../../../services/usersService'

const CAMPOS_INICIALES = { username: '', email: '', first_name: '', last_name: '', password: '', must_change_password: true }

export default function UserFormPage() {
  const { id } = useParams()
  const esEdicion = Boolean(id)
  const navigate = useNavigate()

  const [campos, setCampos] = useState(CAMPOS_INICIALES)
  const [rolesDisponibles, setRolesDisponibles] = useState([])
  const [rolesSeleccionados, setRolesSeleccionados] = useState([])
  const [catalogoModulos, setCatalogoModulos] = useState({})
  const [permisosSeleccionados, setPermisosSeleccionados] = useState([])
  const [cargando, setCargando] = useState(esEdicion)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [exito, setExito] = useState('')

  useEffect(() => {
    const catalogoYRoles = Promise.all([permissionsService.catalog(), rolesService.list()])

    if (esEdicion) {
      Promise.all([usersService.get(id), catalogoYRoles])
        .then(([usuario, [catalogo, rolesData]]) => {
          setCatalogoModulos(catalogo.modules)
          setRolesDisponibles(rolesData.results)
          setCampos({
            username: usuario.username, email: usuario.email,
            first_name: usuario.first_name, last_name: usuario.last_name,
            password: '', must_change_password: usuario.must_change_password,
          })
          setPermisosSeleccionados(usuario.direct_permissions)
          setRolesSeleccionados(rolesData.results.filter((r) => usuario.roles.includes(r.name)).map((r) => r.id))
        })
        .catch(() => setError('No se pudo cargar el usuario.'))
        .finally(() => setCargando(false))
    } else {
      catalogoYRoles.then(([catalogo, rolesData]) => {
        setCatalogoModulos(catalogo.modules)
        setRolesDisponibles(rolesData.results)
      })
    }
  }, [id, esEdicion])

  const alternarRol = (roleId) => {
    setRolesSeleccionados((prev) => (prev.includes(roleId) ? prev.filter((r) => r !== roleId) : [...prev, roleId]))
  }

  const alternarPermiso = (codename) => {
    setPermisosSeleccionados((prev) => (prev.includes(codename) ? prev.filter((p) => p !== codename) : [...prev, codename]))
  }

  const enviar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')
    setExito('')
    try {
      if (esEdicion) {
        await usersService.update(id, { email: campos.email, first_name: campos.first_name, last_name: campos.last_name })
        await usersService.assignRoles(id, rolesSeleccionados)
        await usersService.assignPermissions(id, permisosSeleccionados)
        setExito('Cambios guardados.')
      } else {
        await usersService.create({
          username: campos.username, email: campos.email, first_name: campos.first_name,
          last_name: campos.last_name, password: campos.password, must_change_password: campos.must_change_password,
        })
        navigate('/admin/users')
      }
    } catch (err) {
      setError(err.response?.data?.mensaje || 'No se pudo guardar el usuario.')
    } finally {
      setGuardando(false)
    }
  }

  if (cargando) return <div className="text-center py-4"><Spinner animation="border" /></div>

  return (
    <div>
      <h1 className="h4 mb-3">{esEdicion ? 'Editar usuario' : 'Nuevo usuario'}</h1>
      {error && <Alert variant="danger">{error}</Alert>}
      {exito && <Alert variant="success">{exito}</Alert>}

      <Form onSubmit={enviar}>
        <Card className="chart-panel mb-3">
          <h6>Datos generales</h6>
          {!esEdicion && (
            <Form.Group className="mb-2" controlId="user-username">
              <Form.Label>Nombre de usuario</Form.Label>
              <Form.Control value={campos.username} onChange={(e) => setCampos({ ...campos, username: e.target.value })} required />
            </Form.Group>
          )}
          <Form.Group className="mb-2" controlId="user-email">
            <Form.Label>Correo</Form.Label>
            <Form.Control type="email" value={campos.email} onChange={(e) => setCampos({ ...campos, email: e.target.value })} required />
          </Form.Group>
          <Form.Group className="mb-2" controlId="user-first-name">
            <Form.Label>Nombre</Form.Label>
            <Form.Control value={campos.first_name} onChange={(e) => setCampos({ ...campos, first_name: e.target.value })} />
          </Form.Group>
          <Form.Group className="mb-2" controlId="user-last-name">
            <Form.Label>Apellido</Form.Label>
            <Form.Control value={campos.last_name} onChange={(e) => setCampos({ ...campos, last_name: e.target.value })} />
          </Form.Group>
          {!esEdicion && (
            <>
              <Form.Group className="mb-2" controlId="user-password">
                <Form.Label>Contraseña</Form.Label>
                <Form.Control type="password" value={campos.password} onChange={(e) => setCampos({ ...campos, password: e.target.value })} required minLength={8} />
              </Form.Group>
              <Form.Check
                type="checkbox"
                id="user-must-change-password"
                label="Exigir cambio de contraseña en el próximo inicio de sesión"
                checked={campos.must_change_password}
                onChange={(e) => setCampos({ ...campos, must_change_password: e.target.checked })}
              />
            </>
          )}
        </Card>

        {esEdicion && (
          <>
            <Card className="chart-panel mb-3">
              <h6>Roles</h6>
              {rolesDisponibles.length === 0 && <div className="chart-panel__subtitle">No hay roles creados todavía.</div>}
              {rolesDisponibles.map((rol) => (
                <Form.Check
                  key={rol.id}
                  type="checkbox"
                  id={`rol-${rol.id}`}
                  label={rol.name}
                  checked={rolesSeleccionados.includes(rol.id)}
                  onChange={() => alternarRol(rol.id)}
                />
              ))}
            </Card>

            <Card className="chart-panel mb-3">
              <h6>Permisos directos (además de los que otorgan sus roles)</h6>
              {Object.entries(catalogoModulos).map(([modulo, permisos]) => (
                <div key={modulo} className="mb-2">
                  <div className="fw-semibold text-capitalize" style={{ fontSize: '0.85rem' }}>{modulo}</div>
                  {permisos.map((p) => (
                    <Form.Check
                      key={p.codename}
                      type="checkbox"
                      id={`permiso-${p.codename}`}
                      label={p.name}
                      checked={permisosSeleccionados.includes(p.codename)}
                      onChange={() => alternarPermiso(p.codename)}
                    />
                  ))}
                </div>
              ))}
            </Card>
          </>
        )}

        <Button type="submit" disabled={guardando}>
          {guardando ? <Spinner size="sm" animation="border" /> : 'Guardar'}
        </Button>
      </Form>
    </div>
  )
}
