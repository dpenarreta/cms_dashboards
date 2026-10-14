import { Link, NavLink } from 'react-router-dom'
import { useAdminMenu } from '../../hooks/useAdminMenu'
import { useAuth } from '../../context/AuthContext'
import { useMarca } from '../../hooks/useMarca'
import { useColorMode } from '../../hooks/useColorMode'
import { NOMBRE_SITIO_POR_DEFECTO, inicialesDeMarca } from '../../utils/marca'

/** Rol que se muestra en la píldora del pie: solo informativo (el acceso real lo deciden los
 * permisos, nunca el nombre de un rol). */
function rolVisible(user) {
  if (user?.is_superuser) return 'Superusuario'
  return user?.roles?.[0] || null
}

/**
 * Menú lateral con la estructura de la Matriz (`mz-sidebar`): logotipo, ítems con ícono y, al
 * pie, el botón de tema claro/oscuro, el rol y el usuario con su botón de cerrar sesión. Siempre azul institucional, en los dos
 * modos. En pantallas de 880px o menos se oculta y lo abre el botón de menú de la barra superior
 * (`AdminLayout`), que es quien guarda si está abierto.
 */
export default function AdminSidebar({ abierto = false, onCerrar = () => {} }) {
  const items = useAdminMenu()
  const { user, logout } = useAuth()
  const theme = useMarca()
  const { oscuro, alternar: alternarTema } = useColorMode()

  const inicial = (user?.username || '?').charAt(0).toUpperCase()
  // Refleja de inmediato un nombre editado desde /admin/profile (`ProfilePage.jsx` llama
  // `refreshUser()` al guardar, que actualiza este mismo `user` global) — sin nombre/apellido
  // cargados, cae al username de siempre.
  const nombreMostrado = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username
  const rol = rolVisible(user)
  const claseItem = ({ isActive }) => `mz-nav-item ${isActive ? 'is-active' : ''}`

  return (
    <>
      <nav className={`mz-sidebar d-print-none ${abierto ? 'mz-sidebar--open' : ''}`} aria-label="Menú principal">
        <div className="mz-brand">
          {theme?.logo_url
            ? <img src={theme.logo_url} alt="" className="mz-brand-logo" />
            : <span className="mz-glyph" aria-hidden="true">{inicialesDeMarca(theme)}</span>}
          <span>{theme?.site_name || NOMBRE_SITIO_POR_DEFECTO}</span>
        </div>

        <ul className="mz-nav">
          <li>
            <NavLink to="/app/dashboards" className={claseItem} onClick={onCerrar}>
              <i className="bi bi-bar-chart-line" aria-hidden="true"></i>
              <span>Dashboards</span>
            </NavLink>
          </li>
          {items.map((item) => (
            <li key={item.id}>
              <NavLink to={item.path} className={claseItem} onClick={onCerrar}>
                <i className={`bi ${item.icon}`} aria-hidden="true"></i>
                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>

        {/* Siempre al pie del menú (la lista de arriba ocupa el espacio libre, así que queda abajo
            aunque haya pocos ítems), nunca en la barra superior: tema, rol, usuario y cerrar sesión. */}
        <div className="mz-sidebar-foot">
          <button
            type="button" className="mz-nav-item mz-theme-toggle"
            aria-label={oscuro ? 'Tema claro' : 'Tema oscuro'}
            title={oscuro ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
            onClick={alternarTema}
          >
            <i className={`bi ${oscuro ? 'bi-sun' : 'bi-moon-stars'}`} aria-hidden="true"></i>
            <span>{oscuro ? 'Tema claro' : 'Tema oscuro'}</span>
          </button>
          {rol && <span className="mz-role-pill"><i className="bi bi-shield-lock" aria-hidden="true"></i> {rol}</span>}
          <div className="mz-user">
            <Link to="/admin/profile" className="mz-user-link" title="Ver mi perfil" onClick={onCerrar}>
              <div className="mz-avatar" aria-hidden="true">
                {user?.avatar_url ? <img src={user.avatar_url} alt="" /> : inicial}
              </div>
              <div>
                <strong>{nombreMostrado}</strong>
                {user?.email && <span>{user.email}</span>}
              </div>
            </Link>
            <button type="button" className="mz-logout" aria-label="Cerrar sesión" title="Cerrar sesión" onClick={logout}>
              <i className="bi bi-box-arrow-right" aria-hidden="true"></i>
            </button>
          </div>
        </div>
      </nav>
      {abierto && <button type="button" className="mz-sidebar-backdrop" aria-label="Cerrar menú" onClick={onCerrar} />}
    </>
  )
}
