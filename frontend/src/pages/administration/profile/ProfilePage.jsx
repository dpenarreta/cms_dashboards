import { useRef, useState } from 'react'
import { Alert, Badge, Button, Card, Form, Spinner } from 'react-bootstrap'
import { useAuth } from '../../../context/AuthContext'
import * as authService from '../../../services/authService'

function extraerMensajeError(e, porDefecto) {
  const data = e.response?.data
  if (!data) return porDefecto
  if (data.mensaje) return data.mensaje
  const primerCampo = Object.values(data)[0]
  if (Array.isArray(primerCampo) && typeof primerCampo[0] === 'string') return primerCampo[0]
  return porDefecto
}

const CAMPOS_PASSWORD_INICIALES = { oldPassword: '', newPassword: '', confirmPassword: '' }

export default function ProfilePage() {
  const { user, refreshUser } = useAuth()

  const [nombre, setNombre] = useState(user?.first_name || '')
  const [apellido, setApellido] = useState(user?.last_name || '')
  const [username, setUsername] = useState(user?.username || '')
  const [area, setArea] = useState(user?.area || '')
  const [guardandoDatos, setGuardandoDatos] = useState(false)
  const [errorDatos, setErrorDatos] = useState('')
  const [exitoDatos, setExitoDatos] = useState('')

  const inputArchivoRef = useRef(null)
  const [archivoSeleccionado, setArchivoSeleccionado] = useState(null)
  const [previsualizacion, setPrevisualizacion] = useState(null)
  const [subiendoAvatar, setSubiendoAvatar] = useState(false)
  const [errorAvatar, setErrorAvatar] = useState('')

  const [campoPassword, setCampoPassword] = useState(CAMPOS_PASSWORD_INICIALES)
  const [cambiandoPassword, setCambiandoPassword] = useState(false)
  const [errorPassword, setErrorPassword] = useState('')
  const [exitoPassword, setExitoPassword] = useState('')

  const inicial = (user?.username || '?').charAt(0).toUpperCase()
  const nombreCompleto = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username

  const elegirArchivo = (e) => {
    const archivo = e.target.files?.[0] || null
    setArchivoSeleccionado(archivo)
    setErrorAvatar('')
    setPrevisualizacion(archivo ? URL.createObjectURL(archivo) : null)
  }

  const guardarDatos = async (e) => {
    e.preventDefault()
    setGuardandoDatos(true)
    setErrorDatos('')
    setExitoDatos('')
    try {
      await authService.updateProfile({ area, firstName: nombre, lastName: apellido, username })
      await refreshUser()
      setExitoDatos('Datos actualizados.')
    } catch (err) {
      setErrorDatos(extraerMensajeError(err, 'No se pudo actualizar el perfil.'))
    } finally {
      setGuardandoDatos(false)
    }
  }

  const subirAvatar = async () => {
    if (!archivoSeleccionado) return
    setSubiendoAvatar(true)
    setErrorAvatar('')
    try {
      await authService.uploadAvatar(archivoSeleccionado)
      await refreshUser()
      setArchivoSeleccionado(null)
      setPrevisualizacion(null)
      if (inputArchivoRef.current) inputArchivoRef.current.value = ''
    } catch (err) {
      setErrorAvatar(extraerMensajeError(err, 'No se pudo subir la imagen.'))
    } finally {
      setSubiendoAvatar(false)
    }
  }

  const cambiarPassword = async (e) => {
    e.preventDefault()
    setErrorPassword('')
    setExitoPassword('')
    if (campoPassword.newPassword !== campoPassword.confirmPassword) {
      setErrorPassword('Las contraseñas no coinciden.')
      return
    }
    setCambiandoPassword(true)
    try {
      await authService.changePassword({ oldPassword: campoPassword.oldPassword, newPassword: campoPassword.newPassword })
      setExitoPassword('Contraseña actualizada.')
      setCampoPassword(CAMPOS_PASSWORD_INICIALES)
    } catch (err) {
      setErrorPassword(extraerMensajeError(err, 'No se pudo cambiar la contraseña.'))
    } finally {
      setCambiandoPassword(false)
    }
  }

  return (
    <div>
      <h1 className="h4 mb-3">Mi perfil</h1>

      <Card className="chart-panel mb-3">
        <div className="d-flex align-items-center gap-3 flex-wrap">
          {previsualizacion || user?.avatar_url ? (
            <img
              src={previsualizacion || user.avatar_url}
              alt="Avatar"
              style={{ width: 72, height: 72, borderRadius: '50%', objectFit: 'cover' }}
            />
          ) : (
            <div
              className="d-flex align-items-center justify-content-center"
              style={{ width: 72, height: 72, borderRadius: '50%', background: 'var(--color-primary)', color: '#fff', fontSize: '1.6rem', fontWeight: 700 }}
            >
              {inicial}
            </div>
          )}
          <div>
            <div className="fw-semibold" style={{ fontSize: '1.1rem' }}>{nombreCompleto}</div>
            <div className="chart-panel__subtitle mb-1">{user?.email}</div>
            <div>
              {user?.roles?.length > 0
                ? user.roles.map((rol) => <Badge key={rol} bg="secondary" className="me-1">{rol}</Badge>)
                : <span className="chart-panel__subtitle">Sin rol asignado</span>}
              {user?.is_superuser && <Badge bg="dark">Superusuario</Badge>}
            </div>
          </div>
        </div>

        <Form.Group className="mt-3" controlId="profile-avatar-file">
          <Form.Label>Cambiar avatar</Form.Label>
          <div className="d-flex gap-2 flex-wrap">
            <Form.Control ref={inputArchivoRef} type="file" accept="image/*" onChange={elegirArchivo} style={{ maxWidth: 320 }} />
            <Button onClick={subirAvatar} disabled={!archivoSeleccionado || subiendoAvatar}>
              {subiendoAvatar ? <Spinner size="sm" animation="border" /> : 'Subir imagen'}
            </Button>
          </div>
          {errorAvatar && <Alert variant="danger" className="mt-2 mb-0">{errorAvatar}</Alert>}
        </Form.Group>
      </Card>

      <Card className="chart-panel mb-3">
        <h6>Datos generales</h6>
        <Form onSubmit={guardarDatos}>
          {errorDatos && <Alert variant="danger">{errorDatos}</Alert>}
          {exitoDatos && <Alert variant="success">{exitoDatos}</Alert>}
          <Form.Group className="mb-2" controlId="profile-first-name">
            <Form.Label>Nombre</Form.Label>
            <Form.Control value={nombre} onChange={(e) => setNombre(e.target.value)} maxLength={150} placeholder="Nombre" />
          </Form.Group>
          <Form.Group className="mb-2" controlId="profile-last-name">
            <Form.Label>Apellido</Form.Label>
            <Form.Control value={apellido} onChange={(e) => setApellido(e.target.value)} maxLength={150} placeholder="Apellido" />
          </Form.Group>
          <Form.Group className="mb-2" controlId="profile-username">
            <Form.Label>Nombre de usuario</Form.Label>
            <Form.Control value={username} onChange={(e) => setUsername(e.target.value)} maxLength={150} required />
          </Form.Group>
          <Form.Group className="mb-2" controlId="profile-email">
            <Form.Label>Correo</Form.Label>
            <Form.Control value={user?.email || ''} disabled />
          </Form.Group>
          <Form.Group className="mb-2" controlId="profile-area">
            <Form.Label>Área</Form.Label>
            <Form.Control value={area} onChange={(e) => setArea(e.target.value)} maxLength={100} placeholder="Ej. Cobranzas" />
          </Form.Group>
          <Button type="submit" disabled={guardandoDatos}>
            {guardandoDatos ? <Spinner size="sm" animation="border" /> : 'Guardar cambios'}
          </Button>
        </Form>
      </Card>

      <Card className="chart-panel mb-3">
        <h6>Cambiar contraseña</h6>
        <Form onSubmit={cambiarPassword}>
          {errorPassword && <Alert variant="danger">{errorPassword}</Alert>}
          {exitoPassword && <Alert variant="success">{exitoPassword}</Alert>}
          <Form.Group className="mb-2" controlId="profile-old-password">
            <Form.Label>Contraseña actual</Form.Label>
            <Form.Control
              type="password"
              value={campoPassword.oldPassword}
              onChange={(e) => setCampoPassword({ ...campoPassword, oldPassword: e.target.value })}
              required
            />
          </Form.Group>
          <Form.Group className="mb-2" controlId="profile-new-password">
            <Form.Label>Contraseña nueva</Form.Label>
            <Form.Control
              type="password"
              value={campoPassword.newPassword}
              onChange={(e) => setCampoPassword({ ...campoPassword, newPassword: e.target.value })}
              required
              minLength={8}
            />
          </Form.Group>
          <Form.Group className="mb-2" controlId="profile-confirm-password">
            <Form.Label>Confirmar contraseña nueva</Form.Label>
            <Form.Control
              type="password"
              value={campoPassword.confirmPassword}
              onChange={(e) => setCampoPassword({ ...campoPassword, confirmPassword: e.target.value })}
              required
              minLength={8}
            />
          </Form.Group>
          <Button type="submit" disabled={cambiandoPassword}>
            {cambiandoPassword ? <Spinner size="sm" animation="border" /> : 'Cambiar contraseña'}
          </Button>
        </Form>
      </Card>
    </div>
  )
}
