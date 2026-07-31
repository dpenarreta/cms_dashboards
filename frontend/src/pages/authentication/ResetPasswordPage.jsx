import { useEffect, useState } from 'react'
import { Alert, Button, Card, Form, Spinner } from 'react-bootstrap'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import * as authService from '../../services/authService'

const LONGITUD_MINIMA = 8

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''

  const [validando, setValidando] = useState(true)
  const [tokenValido, setTokenValido] = useState(false)

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [completado, setCompletado] = useState(false)

  useEffect(() => {
    if (!token) {
      setValidando(false)
      setTokenValido(false)
      return
    }
    authService.validatePasswordResetToken(token)
      .then(() => setTokenValido(true))
      .catch(() => setTokenValido(false))
      .finally(() => setValidando(false))
  }, [token])

  const noCoinciden = confirmPassword.length > 0 && newPassword !== confirmPassword
  const muyCorta = newPassword.length > 0 && newPassword.length < LONGITUD_MINIMA

  const enviar = async (e) => {
    e.preventDefault()
    if (noCoinciden || muyCorta) return
    setEnviando(true)
    setError('')
    try {
      await authService.confirmPasswordReset({ token, newPassword, confirmPassword })
      setCompletado(true)
      setTimeout(() => navigate('/login', { replace: true }), 2500)
    } catch (err) {
      setError(err.response?.data?.mensaje || 'No se pudo restablecer la contraseña. El enlace puede haber expirado.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="d-flex align-items-center justify-content-center" style={{ minHeight: '100vh' }}>
      <Card style={{ width: 380 }} className="p-4 shadow-sm">
        <Card.Title className="mb-3 text-center">Restablecer contraseña</Card.Title>

        {validando && (
          <div className="text-center py-3" role="status" aria-live="polite"><Spinner animation="border" size="sm" /></div>
        )}

        {!validando && !tokenValido && !completado && (
          <>
            <Alert variant="danger" role="alert">
              Este enlace de recuperación no es válido o ya expiró.
            </Alert>
            <div className="text-center">
              <Link to="/forgot-password">Solicitar un nuevo enlace</Link>
            </div>
          </>
        )}

        {!validando && tokenValido && completado && (
          <Alert variant="success" role="status">
            Tu contraseña fue actualizada correctamente. Te redirigiremos al inicio de sesión.
          </Alert>
        )}

        {!validando && tokenValido && !completado && (
          <Form onSubmit={enviar}>
            {error && <Alert variant="danger" role="alert">{error}</Alert>}

            <Form.Group className="mb-3" controlId="reset-password-new">
              <Form.Label>Nueva contraseña</Form.Label>
              <Form.Control
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                isInvalid={muyCorta}
                required
                autoFocus
                disabled={enviando}
              />
              <Form.Control.Feedback type="invalid">
                La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres.
              </Form.Control.Feedback>
            </Form.Group>

            <Form.Group className="mb-3" controlId="reset-password-confirm">
              <Form.Label>Confirmar contraseña</Form.Label>
              <Form.Control
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                isInvalid={noCoinciden}
                required
                disabled={enviando}
              />
              <Form.Control.Feedback type="invalid">Las contraseñas no coinciden.</Form.Control.Feedback>
            </Form.Group>

            <Button type="submit" variant="primary" className="w-100" disabled={enviando}>
              {enviando ? <Spinner size="sm" animation="border" aria-hidden="true" /> : 'Restablecer contraseña'}
            </Button>
          </Form>
        )}
      </Card>
    </div>
  )
}
