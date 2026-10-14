import { useMarca } from '../../hooks/useMarca'
import { NOMBRE_SITIO_POR_DEFECTO, inicialesDeMarca } from '../../utils/marca'

/**
 * Esqueleto de la pantalla de acceso de la Matriz (`login-screen`): panel azul con la marca y el
 * mensaje a la izquierda (se oculta en 880px o menos) y la tarjeta a la derecha. Lo comparten
 * login, recuperación y restablecimiento de contraseña, y las páginas 403/404.
 */
export default function PantallaAcceso({ titulo, subtitulo, children }) {
  const theme = useMarca()
  const nombre = theme?.site_name || NOMBRE_SITIO_POR_DEFECTO

  return (
    <div className="login-screen">
      <aside className="login-aside">
        <div className="login-brand">
          {theme?.logo_url
            ? <img src={theme.logo_url} alt="" className="login-logo" />
            : <span className="login-glyph" aria-hidden="true">{inicialesDeMarca(theme)}</span>}
          {nombre}
        </div>
        <div className="login-pitch">
          <h1>Indicadores de cartera y gestión, en un solo lugar.</h1>
          <p>Cargue los datos, configure cada dashboard y compártalo con quien lo necesita, según su rol.</p>
        </div>
        <div className="login-foot">Acceso restringido a usuarios autorizados.</div>
      </aside>
      <div className="login-main">
        <div className="login-card">
          <h2>{titulo}</h2>
          {subtitulo && <p className="login-sub">{subtitulo}</p>}
          {children}
        </div>
      </div>
    </div>
  )
}
