/**
 * Menú administrativo: estático en código (mismo patrón que trae skelleton_base), filtrado en el
 * cliente por los permisos del usuario. Ocultar un ítem aquí NO es la protección real — cada
 * página y cada endpoint vuelven a exigir el permiso por su cuenta (`RequirePermission` en
 * frontend, `require_permission(...)` en backend). Esto es solo para no mostrar enlaces a
 * secciones a las que el usuario no puede entrar.
 */
export const ADMIN_MENU = [
  { id: 'usuarios', label: 'Usuarios', icon: '👥', path: '/admin/users', permission: 'usuarios.ver' },
  { id: 'roles', label: 'Roles', icon: '🛡️', path: '/admin/roles', permission: 'roles.ver' },
  { id: 'permisos', label: 'Permisos', icon: '🔑', path: '/admin/permissions', permission: 'permisos.ver' },
  { id: 'configuracion', label: 'Configuración', icon: '⚙️', path: '/admin/settings', permission: 'configuracion.ver' },
  { id: 'auditoria', label: 'Auditoría', icon: '🕵️', path: '/admin/audit', permission: 'auditoria.ver' },
]

export function getVisibleAdminMenu(permissions = []) {
  return ADMIN_MENU.filter((item) => permissions.includes(item.permission))
}
