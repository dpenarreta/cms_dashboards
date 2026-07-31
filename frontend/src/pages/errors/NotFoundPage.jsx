import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="d-flex flex-column align-items-center justify-content-center text-center" style={{ minHeight: '100vh' }}>
      <h1>404</h1>
      <p className="chart-panel__subtitle">La página que buscas no existe.</p>
      <Link to="/">Volver al inicio</Link>
    </div>
  )
}
