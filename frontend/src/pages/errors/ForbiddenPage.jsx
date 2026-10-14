import { Link } from 'react-router-dom'

/** 403 con la pantalla de acceso de la Matriz: el usuario puede no tener sesión, así que no va
 * dentro del layout autenticado. */
export default function ForbiddenPage() {
  return (
    <div className="login-screen">
      <div className="login-main">
        <div className="login-card mz-empty">
          <i className="bi bi-shield-lock" aria-hidden="true"></i>
          <h1 className="login-codigo">403</h1>
          <p className="login-sub">No tiene permiso para acceder a esta sección.</p>
          <Link to="/">Volver al inicio</Link>
        </div>
      </div>
    </div>
  )
}
