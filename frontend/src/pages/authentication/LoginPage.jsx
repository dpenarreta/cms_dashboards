import { useState } from 'react'
import { Alert, Button, Card, Form, Spinner } from 'react-bootstrap'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/**
 * Tras iniciar sesión se abre el listado de dashboards, no un dashboard fijo: el listado
 * (`/app/dashboards`) ya muestra únicamente los dashboards a los que el usuario tiene acceso —
 * de lectura o de edición — resueltos en backend (`GET /api/dashboards/authorized`). Apuntar a un
 * dashboard concreto llevaba a un 403 a cualquier usuario sin acceso a ese dashboard puntual.
 */
const RUTA_POR_DEFECTO = '/app/dashboards'

/**
 * A dónde volver después de iniciar sesión, en orden de preferencia:
 *
 * 1. `location.state.from`, que pone `RequirePermission` cuando rebota una navegación interna.
 * 2. `?from=`, que pone `httpClient.redirigirALogin` cuando la sesión vence a mitad de camino —
 *    ese redirect recarga el documento, así que el `state` no sobrevive.
 * 3. El listado de dashboards.
 *
 * Solo se aceptan rutas internas (`/algo`): un `from` con host propio permitiría que un enlace
 * preparado por un tercero mandara al usuario a un dominio externo justo después de autenticarse.
 */
function rutaDeRetorno(location) {
  const desdeEstado = location.state?.from
  if (desdeEstado) return desdeEstado
  const desdeQuery = new URLSearchParams(location.search).get('from')
  if (desdeQuery && desdeQuery.startsWith('/') && !desdeQuery.startsWith('//')) return desdeQuery
  return RUTA_POR_DEFECTO
}

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  if (isAuthenticated) {
    return <Navigate to={rutaDeRetorno(location)} replace />
  }

  const enviar = async (e) => {
    e.preventDefault()
    setCargando(true)
    setError('')
    const resultado = await login({ identifier, password })
    setCargando(false)
    if (!resultado.ok) {
      setError(resultado.error)
      return
    }
    navigate(rutaDeRetorno(location), { replace: true })
  }

  return (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '100vh' }}>
      <Card style={{ width: 380 }} className="p-4 shadow-sm">
        <Card.Title className="mb-3 text-center">Iniciar sesión</Card.Title>
        {error && <Alert variant="danger" role="alert">{error}</Alert>}
        <Form onSubmit={enviar}>
          <Form.Group className="mb-3" controlId="login-identifier">
            <Form.Label>Usuario o correo</Form.Label>
            <Form.Control
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              autoFocus
              disabled={cargando}
            />
          </Form.Group>
          <Form.Group className="mb-3" controlId="login-password">
            <Form.Label>Contraseña</Form.Label>
            <Form.Control
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={cargando}
            />
          </Form.Group>
          <Button type="submit" className="w-100" disabled={cargando}>
            {cargando ? <Spinner size="sm" animation="border" aria-hidden="true" /> : 'Ingresar'}
          </Button>
        </Form>
        <div className="text-center mt-3">
          <Link to="/forgot-password">¿Olvidaste tu contraseña?</Link>
        </div>
      </Card>
    </div>
  )
}
