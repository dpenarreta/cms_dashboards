import { useState } from 'react'
import { Alert, Button, Form, Spinner } from 'react-bootstrap'
import { Link } from 'react-router-dom'
import PantallaAcceso from '../../components/auth/PantallaAcceso'
import * as authService from '../../services/authService'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [cargando, setCargando] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')

  const enviar = async (e) => {
    e.preventDefault()
    setCargando(true)
    setError('')
    setMensaje('')
    try {
      const { message } = await authService.requestPasswordReset(email)
      setMensaje(message)
    } catch {
      setError('No se pudo procesar la solicitud. Intenta de nuevo en unos minutos.')
    } finally {
      setCargando(false)
    }
  }

  return (
    <PantallaAcceso titulo="Recuperar contraseña" subtitulo="Le enviaremos un enlace para crear una contraseña nueva.">

      {mensaje && <Alert variant="success" role="status">{mensaje}</Alert>}
      {error && <Alert variant="danger" role="alert">{error}</Alert>}

      {!mensaje && (
        <Form onSubmit={enviar}>
          <Form.Group className="mb-3" controlId="forgot-password-email">
            <Form.Label>Correo electrónico</Form.Label>
            <Form.Control
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              disabled={cargando}
            />
          </Form.Group>
          <Button type="submit" variant="primary" className="w-100" disabled={cargando}>
            {cargando ? <Spinner size="sm" animation="border" aria-hidden="true" /> : 'Enviar enlace de recuperación'}
          </Button>
        </Form>
      )}

      <div className="text-center mt-3">
        <Link to="/login">Volver al inicio de sesión</Link>
      </div>
    </PantallaAcceso>
  )
}
