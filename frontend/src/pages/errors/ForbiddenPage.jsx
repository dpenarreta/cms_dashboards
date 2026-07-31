import { Link } from 'react-router-dom'

export default function ForbiddenPage() {
  return (
    <div className="d-flex flex-column align-items-center justify-content-center text-center" style={{ minHeight: '100vh' }}>
      <h1>403</h1>
      <p className="chart-panel__subtitle">No tiene permiso para acceder a esta sección.</p>
      <Link to="/">Volver al inicio</Link>
    </div>
  )
}
