import { Link } from 'react-router-dom'

/** 404 con la pantalla de acceso de la Matriz: el usuario puede no tener sesión, así que no va
 * dentro del layout autenticado. */
export default function NotFoundPage() {
  return (
    <div className="login-screen">
      <div className="login-main">
        <div className="login-card mz-empty">
          <i className="bi bi-signpost-split" aria-hidden="true"></i>
          <h1 className="login-codigo">404</h1>
          <p className="login-sub">La página que buscas no existe.</p>
          <Link to="/">Volver al inicio</Link>
        </div>
      </div>
    </div>
  )
}
