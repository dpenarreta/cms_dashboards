import { Button } from 'react-bootstrap'
import { Link, Outlet, useLocation } from 'react-router-dom'
import AdminSidebar from './AdminSidebar'
import '../../styles/admin-sidebar.css'

const RUTA_LISTADO_DASHBOARDS = '/app/dashboards'

/**
 * Layout de pantalla completa de toda la app autenticada (dashboards y administración) — la
 * barra lateral debe verse siempre, en cualquier interfaz, no solo en /admin. Antes existía un
 * `AuthenticatedLayout` separado (barra superior sin sidebar) para /app/dashboards/*; se retiró
 * porque, si el contenido estuviera anidado bajo esa barra compartida, la barra lateral nunca
 * podría abarcar el 100% del alto real de la pantalla (quedaría empujada hacia abajo). Aquí
 * `AdminLayout` es dueño de toda la pantalla: sidebar a la izquierda (100% del alto) + una barra
 * superior propia, más liviana, a la derecha.
 */
export default function AdminLayout() {
  const { pathname } = useLocation()
  // "Volver a Dashboards" no tiene destino útil estando ya en el listado, así que ahí se oculta
  // (antes se mostraba siempre, incluido en la pantalla a la que apunta).
  const mostrarVolver = pathname !== RUTA_LISTADO_DASHBOARDS

  return (
    <div className="admin-shell">
      <AdminSidebar />
      <div className="admin-shell__content">
        <header className="admin-shell__topbar d-print-none">
          {mostrarVolver && (
            <Button as={Link} to={RUTA_LISTADO_DASHBOARDS} size="sm" variant="outline-secondary">
              Volver a Dashboards
            </Button>
          )}
        </header>
        <div className="admin-shell__page">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
