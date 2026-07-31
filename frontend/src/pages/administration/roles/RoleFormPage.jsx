import { useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Spinner } from 'react-bootstrap'
import { useNavigate, useParams } from 'react-router-dom'
import * as permissionsService from '../../../services/permissionsService'
import * as rolesService from '../../../services/rolesService'

export default function RoleFormPage() {
  const { id } = useParams()
  const esEdicion = Boolean(id)
  const navigate = useNavigate()

  const [nombre, setNombre] = useState('')
  const [catalogoModulos, setCatalogoModulos] = useState({})
  const [permisosSeleccionados, setPermisosSeleccionados] = useState([])
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const catalogo = permissionsService.catalog()
    if (esEdicion) {
      Promise.all([rolesService.get(id), catalogo])
        .then(([rol, cat]) => {
          setCatalogoModulos(cat.modules)
          setNombre(rol.name)
          setPermisosSeleccionados(rol.permission_codenames)
        })
        .catch(() => setError('No se pudo cargar el rol.'))
        .finally(() => setCargando(false))
    } else {
      catalogo.then((cat) => setCatalogoModulos(cat.modules)).finally(() => setCargando(false))
    }
  }, [id, esEdicion])

  const alternarPermiso = (codename) => {
    setPermisosSeleccionados((prev) => (prev.includes(codename) ? prev.filter((p) => p !== codename) : [...prev, codename]))
  }

  const enviar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')
    try {
      const payload = { name: nombre, permission_codenames: permisosSeleccionados }
      if (esEdicion) await rolesService.update(id, payload)
      else await rolesService.create(payload)
      navigate('/admin/roles')
    } catch (err) {
      setError(err.response?.data?.mensaje || 'No se pudo guardar el rol.')
    } finally {
      setGuardando(false)
    }
  }

  if (cargando) return <div className="text-center py-4"><Spinner animation="border" /></div>

  return (
    <div>
      <h1 className="h4 mb-3">{esEdicion ? 'Editar rol' : 'Nuevo rol'}</h1>
      {error && <Alert variant="danger">{error}</Alert>}

      <Form onSubmit={enviar}>
        <Card className="chart-panel mb-3">
          <Form.Group className="mb-0" controlId="role-name">
            <Form.Label>Nombre del rol</Form.Label>
            <Form.Control value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          </Form.Group>
        </Card>

        <Card className="chart-panel mb-3">
          <h6>Permisos</h6>
          {Object.entries(catalogoModulos).map(([modulo, permisos]) => (
            <div key={modulo} className="mb-2">
              <div className="fw-semibold text-capitalize" style={{ fontSize: '0.85rem' }}>{modulo}</div>
              {permisos.map((p) => (
                <Form.Check
                  key={p.codename}
                  type="checkbox"
                  id={`role-permiso-${p.codename}`}
                  label={p.name}
                  checked={permisosSeleccionados.includes(p.codename)}
                  onChange={() => alternarPermiso(p.codename)}
                />
              ))}
            </div>
          ))}
        </Card>

        <Button type="submit" disabled={guardando}>
          {guardando ? <Spinner size="sm" animation="border" /> : 'Guardar'}
        </Button>
      </Form>
    </div>
  )
}
