import { useState } from 'react'
import { Alert, Button, Card, Form, Spinner } from 'react-bootstrap'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const DASHBOARD_POR_DEFECTO = '/app/dashboards/cartera'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  if (isAuthenticated) {
    return <Navigate to={location.state?.from || DASHBOARD_POR_DEFECTO} replace />
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
    navigate(location.state?.from || DASHBOARD_POR_DEFECTO, { replace: true })
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
