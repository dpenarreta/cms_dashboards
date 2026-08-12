import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import UsersRolesTabsBar from '../components/admin/UsersRolesTabsBar'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderBarra(permissions, ruta = '/admin/users') {
  useAuth.mockReturnValue({ user: { permissions } })
  return render(<MemoryRouter initialEntries={[ruta]}><UsersRolesTabsBar /></MemoryRouter>)
}

describe('UsersRolesTabsBar', () => {
  beforeEach(() => vi.clearAllMocks())

  it('con ambos permisos, muestra las dos pestañas', () => {
    renderBarra(['usuarios.ver', 'roles.ver'])
    expect(screen.getByRole('link', { name: 'Usuarios' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Roles' })).toBeInTheDocument()
  })

  it('la pestaña que coincide con la ruta actual queda activa', () => {
    renderBarra(['usuarios.ver', 'roles.ver'], '/admin/roles')
    expect(screen.getByRole('link', { name: 'Roles' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Usuarios' })).not.toHaveClass('active')
  })

  it('con un solo permiso, no muestra nada (no hay entre qué alternar)', () => {
    const { container } = renderBarra(['usuarios.ver'])
    expect(container).toBeEmptyDOMElement()
  })

  it('sin ningún permiso, no muestra nada', () => {
    const { container } = renderBarra([])
    expect(container).toBeEmptyDOMElement()
  })

  it('los enlaces apuntan a /admin/users y /admin/roles', () => {
    renderBarra(['usuarios.ver', 'roles.ver'])
    expect(screen.getByRole('link', { name: 'Usuarios' })).toHaveAttribute('href', '/admin/users')
    expect(screen.getByRole('link', { name: 'Roles' })).toHaveAttribute('href', '/admin/roles')
  })
})
