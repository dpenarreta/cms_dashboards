import { Nav } from 'react-bootstrap'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const PESTANAS = [
  { path: '/admin/settings', label: 'Configuración institucional', permission: 'configuracion.ver', exact: true },
  { path: '/admin/settings/plantilla-base', label: 'Plantilla base de dashboards', permission: 'configuracion.ver' },
  { path: '/admin/settings/email-templates', label: 'Plantilla de correo', permission: 'configuracion.ver' },
]

/**
 * Barra de pestañas compartida entre las tres subsecciones de Configuración (`SettingsPage.jsx`,
 * `PlantillaBasePage.jsx`, `EmailTemplatesPage.jsx`) — mismo patrón que `UsersRolesTabsBar`. La
 * pestaña de "Configuración institucional" usa coincidencia exacta de ruta (`exact: true`) porque
 * su path (`/admin/settings`) es prefijo del de las otras dos — sin eso, quedaría marcada activa
 * en cualquier subsección.
 */
export default function SettingsTabsBar() {
  const { user } = useAuth()
  const location = useLocation()
  const visibles = PESTANAS.filter((p) => user?.permissions?.includes(p.permission))
  if (visibles.length < 2) return null

  return (
    <Nav variant="tabs" className="mb-3">
      {visibles.map((p) => (
        <Nav.Item key={p.path}>
          <Nav.Link
            as={Link} to={p.path}
            active={p.exact ? location.pathname === p.path : location.pathname.startsWith(p.path)}
          >
            {p.label}
          </Nav.Link>
        </Nav.Item>
      ))}
    </Nav>
  )
}
