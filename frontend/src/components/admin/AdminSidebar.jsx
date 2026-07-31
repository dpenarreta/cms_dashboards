import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAdminMenu } from '../../hooks/useAdminMenu'
import { useAuth } from '../../context/AuthContext'
import '../../styles/admin-sidebar.css'

const CLAVE_COLAPSADO = 'admin-sidebar-colapsado'

export default function AdminSidebar() {
  const items = useAdminMenu()
  const { user, logout } = useAuth()
  const [colapsado, setColapsado] = useState(() => localStorage.getItem(CLAVE_COLAPSADO) === '1')

  useEffect(() => {
    localStorage.setItem(CLAVE_COLAPSADO, colapsado ? '1' : '0')
  }, [colapsado])

  const inicial = (user?.username || '?').charAt(0).toUpperCase()

  return (
    <aside className={`admin-sidebar ${colapsado ? 'admin-sidebar--colapsado' : ''}`}>
      <button
        type="button"
        className="admin-sidebar__toggle"
        onClick={() => setColapsado((v) => !v)}
        aria-label={colapsado ? 'Expandir menú' : 'Ocultar menú'}
        title={colapsado ? 'Expandir menú' : 'Ocultar menú'}
      >
        {colapsado ? '»' : '«'}
      </button>

      <div className="admin-sidebar__perfil">
        <div className="admin-sidebar__avatar" aria-hidden="true">{inicial}</div>
        <div className="admin-sidebar__nombre">{user?.username}</div>
      </div>

      <nav className="admin-sidebar__nav" aria-label="Menú administrativo">
        <NavLink
          to="/app/dashboards"
          className={({ isActive }) => `admin-sidebar__link ${isActive ? 'admin-sidebar__link--activo' : ''}`}
          title="Dashboards"
        >
          <span className="admin-sidebar__icono" aria-hidden="true">📊</span>
          <span className="admin-sidebar__texto">Dashboards</span>
        </NavLink>

        {items.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) => `admin-sidebar__link ${isActive ? 'admin-sidebar__link--activo' : ''}`}
            title={item.label}
          >
            <span className="admin-sidebar__icono" aria-hidden="true">{item.icon}</span>
            <span className="admin-sidebar__texto">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Siempre en la parte inferior de la barra lateral (`nav` ocupa el espacio flexible de
          arriba, esto queda pegado al fondo) — nunca en la barra superior. */}
      <div className="admin-sidebar__footer">
        <button type="button" className="admin-sidebar__link" title="Cerrar sesión" onClick={logout}>
          <span className="admin-sidebar__icono" aria-hidden="true">⏻</span>
          <span className="admin-sidebar__texto">Cerrar sesión</span>
        </button>
      </div>
    </aside>
  )
}
