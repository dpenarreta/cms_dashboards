import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AdminSidebar from '../components/admin/AdminSidebar'
import { useAuth } from '../context/AuthContext'
import { useMarca } from '../hooks/useMarca'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../hooks/useMarca', () => ({ useMarca: vi.fn() }))

function renderSidebar(usuario = { permissions: ['usuarios.ver', 'roles.ver'], username: 'ana' }, logout = vi.fn()) {
  useAuth.mockReturnValue({ isAuthenticated: true, user: usuario, logout })
  return render(<MemoryRouter><AdminSidebar /></MemoryRouter>)
}

describe('AdminSidebar', () => {
  beforeEach(() => {
    useMarca.mockReturnValue(null)
  })

  it('solo lista los módulos administrativos que el usuario tiene permiso de ver', () => {
    renderSidebar()

    expect(screen.getByText('Usuarios')).toBeInTheDocument()
    expect(screen.queryByText('Permisos')).not.toBeInTheDocument()
  })

  it('"Usuarios" y "Roles" comparten un único ítem de menú (no hay un ítem "Roles" separado), visible con cualquiera de los dos permisos', () => {
    renderSidebar({ permissions: ['roles.ver'], username: 'ana' })

    expect(screen.getByText('Usuarios')).toBeInTheDocument()
    expect(screen.queryByText('Roles')).not.toBeInTheDocument()
  })

  it('sin autenticar, no muestra ningún ítem', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, user: null })
    render(<MemoryRouter><AdminSidebar /></MemoryRouter>)
    expect(screen.queryByText('Usuarios')).not.toBeInTheDocument()
  })

  it('sin nombre/apellido cargados, muestra la inicial del usuario en el avatar y el username', () => {
    renderSidebar({ permissions: [], username: 'roberto' })
    expect(screen.getByText('R')).toBeInTheDocument()
    expect(screen.getByText('roberto')).toBeInTheDocument()
  })

  it('con nombre/apellido cargados (editado desde /admin/profile), muestra el nombre completo en vez del username', () => {
    renderSidebar({ permissions: [], username: 'roberto', first_name: 'Roberto', last_name: 'Gómez' })
    expect(screen.getByText('Roberto Gómez')).toBeInTheDocument()
    expect(screen.queryByText('roberto')).not.toBeInTheDocument()
  })

  it('el bloque de avatar/nombre enlaza a /admin/profile', () => {
    renderSidebar({ permissions: [], username: 'roberto' })
    expect(screen.getByRole('link', { name: /roberto/ })).toHaveAttribute('href', '/admin/profile')
  })

  it('con avatar_url, muestra la imagen en vez de la inicial', () => {
    renderSidebar({ permissions: [], username: 'roberto', avatar_url: 'http://localhost:8000/media/avatars/foto.png' })
    const imagen = screen.getByRole('link', { name: /roberto/ }).querySelector('img')
    expect(imagen).toHaveAttribute('src', 'http://localhost:8000/media/avatars/foto.png')
    expect(screen.queryByText('R')).not.toBeInTheDocument()
  })

  it('incluye un enlace de vuelta a los dashboards', () => {
    renderSidebar()
    expect(screen.getByRole('link', { name: /dashboards/i })).toHaveAttribute('href', '/app/dashboards')
  })

  it('el botón "Cerrar sesión" está al pie del menú y llama a logout al hacer clic', async () => {
    const logout = vi.fn()
    renderSidebar(undefined, logout)

    const boton = screen.getByRole('button', { name: 'Cerrar sesión' })
    expect(boton.closest('.mz-sidebar-foot')).not.toBeNull()

    await userEvent.click(boton)
    expect(logout).toHaveBeenCalled()
  })

  it('al pie muestra el rol (Superusuario o el primer rol asignado) y el correo', () => {
    const { unmount } = renderSidebar({ permissions: [], username: 'ana', email: 'ana@example.com', is_superuser: true, roles: ['Lector'] })
    expect(screen.getByText('Superusuario')).toBeInTheDocument()
    expect(screen.getByText('ana@example.com')).toBeInTheDocument()
    unmount()

    renderSidebar({ permissions: [], username: 'ana', roles: ['Lector'] })
    expect(screen.getByText('Lector')).toBeInTheDocument()
  })

  it('sin logo en la identidad institucional, muestra las iniciales del nombre del sitio', () => {
    useMarca.mockReturnValue({ site_name: 'Dashboards LCE', short_name: '' })
    renderSidebar()
    expect(screen.getByText('DL')).toBeInTheDocument()
    expect(screen.getByText('Dashboards LCE')).toBeInTheDocument()
  })

  it('abierto (pantallas chicas), el fondo y cada enlace cierran el menú', async () => {
    const onCerrar = vi.fn()
    useAuth.mockReturnValue({ isAuthenticated: true, user: { permissions: [], username: 'ana' }, logout: vi.fn() })
    render(<MemoryRouter><AdminSidebar abierto onCerrar={onCerrar} /></MemoryRouter>)

    expect(screen.getByRole('navigation', { name: 'Menú principal' })).toHaveClass('mz-sidebar--open')
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar menú' }))
    await userEvent.click(screen.getByRole('link', { name: /dashboards/i }))
    expect(onCerrar).toHaveBeenCalledTimes(2)
  })

  it('el menú lateral no lleva el botón de tema: está en la barra superior', () => {
    renderSidebar()
    expect(screen.queryByRole('button', { name: /Tema (oscuro|claro)/ })).not.toBeInTheDocument()
  })
})
