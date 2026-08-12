import { Nav } from 'react-bootstrap'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const PESTANAS = [
  { path: '/admin/users', label: 'Usuarios', permission: 'usuarios.ver' },
  { path: '/admin/roles', label: 'Roles', permission: 'roles.ver' },
]

/**
 * Barra de pestañas compartida entre "Usuarios" y "Roles" (`UsersListPage.jsx`/`RolesListPage.jsx`):
 * ambas secciones administran quién puede hacer qué en el sistema (un usuario tiene roles, un rol
 * agrupa permisos), así que en el menú lateral viven bajo un único ítem ("Usuarios",
 * `config/adminMenu.js`) — esta barra es lo que deja moverse entre ambas listas sin volver al
 * menú. Cada pestaña se oculta si el usuario no tiene el permiso de ver esa sección (ocultar acá
 * es solo UI, no la protección real — cada ruta sigue exigiendo el permiso vía
 * `RequirePermission`). Con menos de dos pestañas visibles no hay nada que alternar, así que no
 * se muestra nada (evita una barra de una sola pestaña sin utilidad).
 */
export default function UsersRolesTabsBar() {
  const { user } = useAuth()
  const location = useLocation()
  const visibles = PESTANAS.filter((p) => user?.permissions?.includes(p.permission))
  if (visibles.length < 2) return null

  return (
    <Nav variant="tabs" className="mb-3">
      {visibles.map((p) => (
        <Nav.Item key={p.path}>
          <Nav.Link as={Link} to={p.path} active={location.pathname.startsWith(p.path)}>
            {p.label}
          </Nav.Link>
        </Nav.Item>
      ))}
    </Nav>
  )
}
