import { describe, expect, it } from 'vitest'
import { ADMIN_MENU, getVisibleAdminMenu } from '../config/adminMenu'

describe('adminMenu', () => {
  it('sin permisos, no muestra ningún ítem', () => {
    expect(getVisibleAdminMenu([])).toEqual([])
  })

  it('solo muestra los ítems cuyo permiso tiene el usuario', () => {
    const visibles = getVisibleAdminMenu(['usuarios.ver'])
    expect(visibles).toHaveLength(1)
    expect(visibles[0].id).toBe('usuarios')
  })

  it('"Usuarios" y "Roles" son un único ítem, visible con cualquiera de los dos permisos', () => {
    expect(getVisibleAdminMenu(['usuarios.ver']).map((i) => i.id)).toEqual(['usuarios'])
    expect(getVisibleAdminMenu(['roles.ver']).map((i) => i.id)).toEqual(['usuarios'])
    // Ningún ítem del menú se llama "roles" — el permiso existe, pero no hay un segundo ítem.
    expect(ADMIN_MENU.find((i) => i.id === 'roles')).toBeUndefined()
  })

  it('con todos los permisos, muestra el menú completo', () => {
    const todos = ADMIN_MENU.flatMap((i) => i.permissions)
    expect(getVisibleAdminMenu(todos)).toHaveLength(ADMIN_MENU.length)
  })
})
