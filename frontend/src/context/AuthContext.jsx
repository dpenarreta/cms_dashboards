import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import * as authService from '../services/authService'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '../services/httpClient'

const AuthContext = createContext(null)

/**
 * Sesión global de la aplicación. Al montar, si hay un access token guardado, intenta resolver
 * el perfil (`GET /auth/me`) para restaurar la sesión tras recargar la página; si falla (token
 * inválido/expirado y sin refresh posible), limpia los tokens y queda como no autenticado.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isInitializing, setIsInitializing] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelado = false
    async function inicializar() {
      if (!getAccessToken()) {
        setIsInitializing(false)
        return
      }
      try {
        const perfil = await authService.me()
        if (!cancelado) setUser(perfil)
      } catch {
        clearTokens()
      } finally {
        if (!cancelado) setIsInitializing(false)
      }
    }
    inicializar()
    return () => { cancelado = true }
  }, [])

  const login = useCallback(async ({ identifier, password }) => {
    setError(null)
    try {
      const tokens = await authService.login({ identifier, password })
      setTokens(tokens.access, tokens.refresh)
      const perfil = await authService.me()
      setUser(perfil)
      return { ok: true }
    } catch (e) {
      const mensaje = e.response?.data?.mensaje || 'No se pudo iniciar sesión.'
      setError(mensaje)
      return { ok: false, error: mensaje }
    }
  }, [])

  const logout = useCallback(async () => {
    const refresh = getRefreshToken()
    try {
      if (refresh) await authService.logout(refresh)
    } catch {
      // Aunque falle en el backend, la sesión local se limpia igual.
    } finally {
      clearTokens()
      setUser(null)
    }
  }, [])

  const refreshUser = useCallback(async () => {
    const perfil = await authService.me()
    setUser(perfil)
    return perfil
  }, [])

  const value = {
    user,
    isAuthenticated: Boolean(user),
    isInitializing,
    error,
    login,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const contexto = useContext(AuthContext)
  if (!contexto) throw new Error('useAuth debe usarse dentro de <AuthProvider>.')
  return contexto
}
