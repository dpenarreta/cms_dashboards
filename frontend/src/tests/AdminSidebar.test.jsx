import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AdminSidebar from '../components/admin/AdminSidebar'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderSidebar(usuario = { permissions: ['usuarios.ver', 'roles.ver'], username: 'ana' }, logout = vi.fn()) {
  useAuth.mockReturnValue({ isAuthenticated: true, user: usuario, logout })
  return render(<MemoryRouter><AdminSidebar /></MemoryRouter>)
}

describe('AdminSidebar', () => {
  beforeEach(() => localStorage.clear())

  it('solo lista los módulos administrativos que el usuario tiene permiso de ver', () => {
    renderSidebar()

    expect(screen.getByText('Usuarios')).toBeInTheDocument()
    expect(screen.getByText('Roles')).toBeInTheDocument()
    expect(screen.queryByText('Permisos')).not.toBeInTheDocument()
  })

  it('sin autenticar, no muestra ningún ítem', () => {
    useAuth.mockReturnValue({ isAuthenticated: false, user: null })
    render(<MemoryRouter><AdminSidebar /></MemoryRouter>)
    expect(screen.queryByText('Usuarios')).not.toBeInTheDocument()
  })

  it('muestra la inicial del usuario en el avatar y su nombre completo', () => {
    renderSidebar({ permissions: [], username: 'roberto' })
    expect(screen.getByText('R')).toBeInTheDocument()
    expect(screen.getByText('roberto')).toBeInTheDocument()
  })

  it('incluye un enlace de vuelta a los dashboards', () => {
    renderSidebar()
    expect(screen.getByRole('link', { name: /dashboards/i })).toHaveAttribute('href', '/app/dashboards')
  })

  it('el botón de colapso oculta el menú y se recuerda entre renders (localStorage)', async () => {
    const { unmount } = renderSidebar()

    const boton = screen.getByRole('button', { name: 'Ocultar menú' })
    await userEvent.click(boton)

    expect(screen.getByRole('button', { name: 'Expandir menú' })).toBeInTheDocument()
    expect(localStorage.getItem('admin-sidebar-colapsado')).toBe('1')

    unmount()
    renderSidebar()
    expect(screen.getByRole('button', { name: 'Expandir menú' })).toBeInTheDocument()
  })

  it('el botón "Cerrar sesión" está siempre en el menú (parte inferior) y llama a logout al hacer clic', async () => {
    const logout = vi.fn()
    renderSidebar(undefined, logout)

    const boton = screen.getByRole('button', { name: 'Cerrar sesión' })
    expect(boton.closest('.admin-sidebar__footer')).not.toBeNull()

    await userEvent.click(boton)
    expect(logout).toHaveBeenCalled()
  })
})
