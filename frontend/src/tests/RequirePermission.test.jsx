import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RequirePermission from '../components/auth/RequirePermission'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderConRuta(permission) {
  return render(
    <MemoryRouter initialEntries={['/protegida']}>
      <Routes>
        <Route path="/protegida" element={<RequirePermission permission={permission}>contenido-protegido</RequirePermission>} />
        <Route path="/login" element={<div>pagina-login</div>} />
        <Route path="/403" element={<div>pagina-403</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequirePermission', () => {
  it('mientras inicializa muestra un indicador de carga, no la pantalla protegida ni login', () => {
    // Devolvía `null`, así que al recargar cualquier pantalla el usuario veía una página en
    // blanco y no podía distinguir "está cargando" de "se rompió". Lo importante sigue siendo
    // que NO parpadee a login mientras se resuelve la sesión.
    useAuth.mockReturnValue({ isInitializing: true, isAuthenticated: false, user: null })
    renderConRuta('dashboard.view')

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getByText('Restaurando sesión…')).toBeInTheDocument()
    expect(screen.queryByText('pagina-login')).not.toBeInTheDocument()
    expect(screen.queryByText('contenido-protegido')).not.toBeInTheDocument()
  })

  it('sin autenticar, redirige a /login', () => {
    useAuth.mockReturnValue({ isInitializing: false, isAuthenticated: false, user: null })
    renderConRuta('dashboard.view')
    expect(screen.getByText('pagina-login')).toBeInTheDocument()
  })

  it('autenticado pero sin el permiso requerido, redirige a /403', () => {
    useAuth.mockReturnValue({ isInitializing: false, isAuthenticated: true, user: { permissions: ['otro.permiso'] } })
    renderConRuta('dashboard.view')
    expect(screen.getByText('pagina-403')).toBeInTheDocument()
  })

  it('autenticado y con el permiso requerido, renderiza el contenido', () => {
    useAuth.mockReturnValue({ isInitializing: false, isAuthenticated: true, user: { permissions: ['dashboard.view'] } })
    renderConRuta('dashboard.view')
    expect(screen.getByText('contenido-protegido')).toBeInTheDocument()
  })

  it('sin permiso especificado, alcanza con estar autenticado (ej. listado de dashboards)', () => {
    useAuth.mockReturnValue({ isInitializing: false, isAuthenticated: true, user: { permissions: [] } })
    renderConRuta(undefined)
    expect(screen.getByText('contenido-protegido')).toBeInTheDocument()
  })
})
