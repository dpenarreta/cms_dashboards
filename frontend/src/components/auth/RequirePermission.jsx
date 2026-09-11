import { Spinner } from 'react-bootstrap'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/**
 * Protege una ruta por permiso puntual (no por rol). Un `ADMINISTRADOR_GENERAL` no se reconoce
 * por nombre de rol: llega hasta aquí porque `user.permissions` ya trae el catálogo completo
 * (resuelto en el backend, ver `apps.permissions.authorization`).
 */
export default function RequirePermission({ permission, children }) {
  const { user, isAuthenticated, isInitializing } = useAuth()
  const location = useLocation()

  // Mientras `AuthContext` resuelve `GET /auth/me` para restaurar la sesión, se muestra un
  // indicador de carga. Antes devolvía `null`: al recargar cualquier pantalla el usuario veía una
  // pantalla completamente en blanco, sin forma de distinguir "está cargando" de "se rompió".
  if (isInitializing) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
        <Spinner animation="border" role="status">
          <span className="visually-hidden">Restaurando sesión…</span>
        </Spinner>
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (permission && !user?.permissions?.includes(permission)) return <Navigate to="/403" replace />
  return children
}
