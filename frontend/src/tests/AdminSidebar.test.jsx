import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AdminSidebar from '../components/admin/AdminSidebar'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))
vi.mock('../context/ThemeContext', () => ({ useTheme: vi.fn() }))

function renderSidebar(usuario = { permissions: ['usuarios.ver', 'roles.ver'], username: 'ana' }, logout = vi.fn()) {
  useAuth.mockReturnValue({ isAuthenticated: true, user: usuario, logout })
  return render(<MemoryRouter><AdminSidebar /></MemoryRouter>)
}

describe('AdminSidebar', () => {
  beforeEach(() => {
    localStorage.clear()
    useTheme.mockReturnValue({ theme: null })
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.removeAttribute('data-bs-theme')
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
    expect(screen.getByRole('link', { name: 'roberto' })).toHaveAttribute('href', '/admin/profile')
  })

  it('con avatar_url, muestra la imagen en vez de la inicial', () => {
    renderSidebar({ permissions: [], username: 'roberto', avatar_url: 'http://localhost:8000/media/avatars/foto.png' })
    const imagen = screen.getByRole('link', { name: 'roberto' }).querySelector('img')
    expect(imagen).toHaveAttribute('src', 'http://localhost:8000/media/avatars/foto.png')
    expect(screen.queryByText('R')).not.toBeInTheDocument()
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

  describe('tema claro/oscuro', () => {
    it('sin preferencia guardada, muestra el botón para pasar a tema oscuro', () => {
      renderSidebar()
      expect(screen.getByRole('button', { name: 'Tema oscuro' })).toBeInTheDocument()
    })

    it('clic en el botón activa el tema oscuro para toda la página (data-theme/data-bs-theme) y lo persiste', async () => {
      renderSidebar()
      await userEvent.click(screen.getByRole('button', { name: 'Tema oscuro' }))

      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
      expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark')
      expect(localStorage.getItem('tema-color-modo')).toBe('1')
      expect(screen.getByRole('button', { name: 'Tema claro' })).toBeInTheDocument()
    })

    it('con el tema oscuro ya guardado, arranca mostrando el botón para volver al claro', () => {
      localStorage.setItem('tema-color-modo', '1')
      renderSidebar()
      expect(screen.getByRole('button', { name: 'Tema claro' })).toBeInTheDocument()
    })

    it('el botón de tema está siempre en el menú (parte inferior), junto a "Cerrar sesión"', () => {
      renderSidebar()
      const boton = screen.getByRole('button', { name: 'Tema oscuro' })
      expect(boton.closest('.admin-sidebar__footer')).not.toBeNull()
    })
  })
})
