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

  it('con todos los permisos, muestra el menú completo', () => {
    const todos = ADMIN_MENU.map((i) => i.permission)
    expect(getVisibleAdminMenu(todos)).toHaveLength(ADMIN_MENU.length)
  })
})
