/**
 * Menú administrativo: estático en código (mismo patrón que trae skelleton_base), filtrado en el
 * cliente por los permisos del usuario. Ocultar un ítem aquí NO es la protección real — cada
 * página y cada endpoint vuelven a exigir el permiso por su cuenta (`RequirePermission` en
 * frontend, `require_permission(...)` en backend). Esto es solo para no mostrar enlaces a
 * secciones a las que el usuario no puede entrar.
 *
 * "Usuarios" y "Roles" son un único ítem (`permissions` con las dos entradas, visible si el
 * usuario tiene CUALQUIERA de las dos — no hace falta tener ambos permisos): ambas secciones
 * administran quién puede hacer qué, así que comparten un mismo lugar en el menú y se navega
 * entre ellas con `UsersRolesTabsBar` (`components/admin/`), no con dos ítems de menú separados.
 * `icon` es una clase de Bootstrap Icons (`bi-*`), como en el menú de la Matriz.
 * El resto de ítems sigue con un único permiso, en un array de un elemento por uniformidad de
 * esquema (siempre `permissions`, nunca `permission` singular).
 */
export const ADMIN_MENU = [
  { id: 'usuarios', label: 'Usuarios', icon: 'bi-people', path: '/admin/users', permissions: ['usuarios.ver', 'roles.ver'] },
  { id: 'permisos', label: 'Permisos', icon: 'bi-key', path: '/admin/permissions', permissions: ['permisos.ver'] },
  { id: 'configuracion', label: 'Configuración', icon: 'bi-gear', path: '/admin/settings', permissions: ['configuracion.ver'] },
  { id: 'auditoria', label: 'Auditoría', icon: 'bi-journal-text', path: '/admin/audit', permissions: ['auditoria.ver'] },
]

export function getVisibleAdminMenu(permissions = []) {
  return ADMIN_MENU.filter((item) => item.permissions.some((p) => permissions.includes(p)))
}
