import { useState } from 'react'
import { Button } from 'react-bootstrap'
import { Link, Outlet, useLocation } from 'react-router-dom'
import AdminSidebar from './AdminSidebar'

const RUTA_LISTADO_DASHBOARDS = '/app/dashboards'

// Título de la barra superior según la sección. El primer prefijo que coincide gana, por eso los
// más específicos van antes.
const TITULOS_POR_RUTA = [
  ['/app/dashboards', 'Dashboards'],
  ['/admin/users', 'Usuarios y roles'],
  ['/admin/roles', 'Usuarios y roles'],
  ['/admin/permissions', 'Permisos'],
  ['/admin/settings', 'Configuración'],
  ['/admin/audit', 'Auditoría'],
  ['/admin/profile', 'Mi perfil'],
]

function tituloDeRuta(pathname) {
  return TITULOS_POR_RUTA.find(([prefijo]) => pathname.startsWith(prefijo))?.[1] || ''
}

/**
 * Layout de toda la app autenticada (dashboards y administración) con la estructura de la Matriz:
 * `mz-shell` = menú lateral (100% del alto) + `mz-main` con la barra superior y la vista. La barra
 * lateral debe verse siempre, en cualquier interfaz, no solo en /admin — por eso este layout es
 * dueño de toda la pantalla y no hay una barra superior compartida por encima.
 *
 * La barra superior lleva el título de la sección y "Volver a Dashboards"; el botón de tema
 * claro/oscuro va al pie del menú lateral. En pantallas de 880px o menos suma el botón que abre
 * el menú.
 */
export default function AdminLayout() {
  const { pathname } = useLocation()
  const [menuAbierto, setMenuAbierto] = useState(false)
  // "Volver a Dashboards" no tiene destino útil estando ya en el listado, así que ahí se oculta.
  const mostrarVolver = pathname !== RUTA_LISTADO_DASHBOARDS

  return (
    <div className="mz-shell">
      <AdminSidebar abierto={menuAbierto} onCerrar={() => setMenuAbierto(false)} />
      <div className="mz-main">
        <header className="mz-topbar d-print-none">
          <button
            type="button" className="mz-icon-btn mz-menu-btn" aria-label="Abrir menú"
            onClick={() => setMenuAbierto(true)}
          >
            <i className="bi bi-list" aria-hidden="true"></i>
          </button>
          <h1>{tituloDeRuta(pathname)}</h1>
          <div className="mz-spacer" />
          {mostrarVolver && (
            <Button as={Link} to={RUTA_LISTADO_DASHBOARDS} size="sm" variant="outline-secondary">
              Volver a Dashboards
            </Button>
          )}
        </header>
        <main className="mz-view">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
