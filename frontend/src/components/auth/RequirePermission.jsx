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

  if (isInitializing) return null
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (permission && !user?.permissions?.includes(permission)) return <Navigate to="/403" replace />
  return children
}
