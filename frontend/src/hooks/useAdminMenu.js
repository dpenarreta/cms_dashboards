import { getVisibleAdminMenu } from '../config/adminMenu'
import { useAuth } from '../context/AuthContext'

export function useAdminMenu() {
  const { user, isAuthenticated } = useAuth()
  if (!isAuthenticated) return []
  return getVisibleAdminMenu(user?.permissions || [])
}
