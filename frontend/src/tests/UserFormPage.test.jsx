import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import UserFormPage from '../pages/administration/users/UserFormPage'
import * as permissionsService from '../services/permissionsService'
import * as rolesService from '../services/rolesService'
import * as usersService from '../services/usersService'
import { useAuth } from '../context/AuthContext'

vi.mock('../services/usersService')
vi.mock('../services/rolesService')
vi.mock('../services/permissionsService')
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const CATALOGO = { modules: { usuarios: [{ codename: 'usuarios.ver', name: 'Ver usuarios' }] } }
const CATALOGO_COMPLETO = {
  modules: {
    usuarios: [
      { codename: 'usuarios.ver', name: 'Ver usuarios' },
      { codename: 'usuarios.crear', name: 'Crear usuarios' },
    ],
    dashboard: [{ codename: 'dashboard.view', name: 'Ver dashboards' }],
  },
}
const ROLES = { results: [{ id: 1, name: 'Cobranzas', permission_codenames: [] }], count: 1, next: null, previous: null }
const ROLES_CON_PERMISOS = {
  results: [
    { id: 1, name: 'Cobranzas', permission_codenames: ['usuarios.ver', 'dashboard.view'] },
    { id: 2, name: 'Sin nada', permission_codenames: [] },
  ],
  count: 2, next: null, previous: null,
}

function renderCrear() {
  return render(
    <MemoryRouter initialEntries={['/admin/users/new']}>
      <Routes><Route path="/admin/users/new" element={<UserFormPage />} /></Routes>
    </MemoryRouter>,
  )
}

function renderEditar() {
  return render(
    <MemoryRouter initialEntries={['/admin/users/7']}>
      <Routes><Route path="/admin/users/:id" element={<UserFormPage />} /></Routes>
    </MemoryRouter>,
  )
}

describe('UserFormPage — creación', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { is_superuser: false } })
  })

  it('envía los datos del nuevo usuario', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.list.mockResolvedValue(ROLES)
    usersService.create.mockResolvedValue({})
    renderCrear()

    await userEvent.type(screen.getByLabelText('Nombre de usuario'), 'nuevo')
    await userEvent.type(screen.getByLabelText('Correo'), 'nuevo@example.com')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Segura-123')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(usersService.create).toHaveBeenCalledWith(expect.objectContaining({
      username: 'nuevo', email: 'nuevo@example.com', password: 'Clave-Segura-123', must_change_password: true,
    })))
  })

  /**
   * Antes el rol se asignaba recién al editar: había que guardar el usuario y volver a entrar,
   * y entre una cosa y la otra la cuenta existía sin ningún rol.
   */
  it('el rol se elige en el alta y viaja en la misma petición', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO_COMPLETO)
    rolesService.list.mockResolvedValue(ROLES_CON_PERMISOS)
    usersService.create.mockResolvedValue({})
    renderCrear()
    await waitFor(() => expect(screen.getByLabelText('Cobranzas')).toBeInTheDocument())

    await userEvent.type(screen.getByLabelText('Nombre de usuario'), 'nuevo')
    await userEvent.type(screen.getByLabelText('Correo'), 'nuevo@example.com')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Segura-123')
    await userEvent.click(screen.getByLabelText('Cobranzas'))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(usersService.create).toHaveBeenCalledWith(
      expect.objectContaining({ role_ids: [1] }),
    ))
    // Una sola operación: sin una segunda llamada que pueda fallar dejando la cuenta sin rol.
    expect(usersService.assignRoles).not.toHaveBeenCalled()
  })

  it('sin rol elegido no se manda ninguno', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO_COMPLETO)
    rolesService.list.mockResolvedValue(ROLES_CON_PERMISOS)
    usersService.create.mockResolvedValue({})
    renderCrear()
    await waitFor(() => expect(screen.getByLabelText('Cobranzas')).toBeInTheDocument())

    await userEvent.type(screen.getByLabelText('Nombre de usuario'), 'nuevo')
    await userEvent.type(screen.getByLabelText('Correo'), 'nuevo@example.com')
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Segura-123')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(usersService.create).toHaveBeenCalledWith(
      expect.objectContaining({ role_ids: [] }),
    ))
  })

  /**
   * La lista solo mostraba nombres ("Cobranzas"), y saber qué significaba cada uno obligaba a
   * abrir la pantalla de roles en otra pestaña. Los nombres salen del catálogo, no del codename.
   */
  it('cada rol dice qué permisos otorga, con el nombre legible de cada uno', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO_COMPLETO)
    rolesService.list.mockResolvedValue(ROLES_CON_PERMISOS)
    renderCrear()

    await waitFor(() => expect(screen.getByLabelText('Cobranzas')).toBeInTheDocument())
    expect(screen.getByText(/Otorga 2 permisos: Ver usuarios, Ver dashboards/)).toBeInTheDocument()
  })

  it('un rol sin permisos lo dice en vez de quedar en blanco', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO_COMPLETO)
    rolesService.list.mockResolvedValue(ROLES_CON_PERMISOS)
    renderCrear()

    await waitFor(() => expect(screen.getByLabelText('Sin nada')).toBeInTheDocument())
    expect(screen.getByText('No otorga ningún permiso todavía.')).toBeInTheDocument()
  })

  it('con muchos permisos nombra unos pocos y resume el resto', async () => {
    // El catálogo entero son 29: listarlos todos bajo cada rol es un muro de texto.
    const codenames = ['a.1', 'a.2', 'a.3', 'a.4', 'a.5', 'a.6', 'a.7']
    permissionsService.catalog.mockResolvedValue(CATALOGO_COMPLETO)
    rolesService.list.mockResolvedValue({
      results: [{ id: 1, name: 'Todopoderoso', permission_codenames: codenames }],
      count: 1, next: null, previous: null,
    })
    renderCrear()

    await waitFor(() => expect(screen.getByLabelText('Todopoderoso')).toBeInTheDocument())
    expect(screen.getByText(/Otorga 7 permisos: a\.1, a\.2, a\.3, a\.4, a\.5 y 2 más\./)).toBeInTheDocument()
  })
})

describe('UserFormPage — edición', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { is_superuser: false } })
  })

  const usuarioDetalle = {
    id: 7, username: 'ana', email: 'ana@example.com', first_name: 'Ana', last_name: 'Pérez',
    status: 'active', roles: ['Cobranzas'], permissions: ['dashboard.view'], direct_permissions: ['dashboard.view'],
    must_change_password: false, is_superuser: false,
  }

  it('precarga los datos, roles y permisos del usuario', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.list.mockResolvedValue(ROLES)
    usersService.get.mockResolvedValue(usuarioDetalle)
    renderEditar()

    expect(await screen.findByDisplayValue('ana@example.com')).toBeInTheDocument()
    expect(screen.getByLabelText('Cobranzas')).toBeChecked()
  })

  it('al guardar, actualiza datos, roles y permisos', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.list.mockResolvedValue(ROLES)
    usersService.get.mockResolvedValue(usuarioDetalle)
    usersService.update.mockResolvedValue({})
    usersService.assignRoles.mockResolvedValue({})
    usersService.assignPermissions.mockResolvedValue({})
    renderEditar()

    await screen.findByDisplayValue('ana@example.com')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => {
      expect(usersService.update).toHaveBeenCalledWith('7', expect.objectContaining({ email: 'ana@example.com' }))
      expect(usersService.assignRoles).toHaveBeenCalledWith('7', [1])
      expect(usersService.assignPermissions).toHaveBeenCalledWith('7', ['dashboard.view'])
    })
  })

  it('un actor sin superusuario no ve el control "Superusuario"', async () => {
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.list.mockResolvedValue(ROLES)
    usersService.get.mockResolvedValue(usuarioDetalle)
    renderEditar()

    await screen.findByDisplayValue('ana@example.com')
    expect(screen.queryByLabelText('Superusuario')).not.toBeInTheDocument()
  })

  it('un actor superusuario ve el control, precargado con el valor del usuario editado', async () => {
    useAuth.mockReturnValue({ user: { is_superuser: true } })
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.list.mockResolvedValue(ROLES)
    usersService.get.mockResolvedValue({ ...usuarioDetalle, is_superuser: true })
    renderEditar()

    await screen.findByDisplayValue('ana@example.com')
    expect(screen.getByLabelText('Superusuario')).toBeChecked()
  })

  it('un actor superusuario puede otorgar superusuario al guardar', async () => {
    useAuth.mockReturnValue({ user: { is_superuser: true } })
    permissionsService.catalog.mockResolvedValue(CATALOGO)
    rolesService.list.mockResolvedValue(ROLES)
    usersService.get.mockResolvedValue(usuarioDetalle)
    usersService.update.mockResolvedValue({})
    usersService.assignRoles.mockResolvedValue({})
    usersService.assignPermissions.mockResolvedValue({})
    usersService.setSuperuser.mockResolvedValue({})
    renderEditar()

    await screen.findByDisplayValue('ana@example.com')
    await userEvent.click(screen.getByLabelText('Superusuario'))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() => expect(usersService.setSuperuser).toHaveBeenCalledWith('7', true))
  })
})
