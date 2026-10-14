import { useEffect, useState } from 'react'
import { Alert, Spinner, Table } from 'react-bootstrap'
import * as permissionsService from '../../../services/permissionsService'

export default function PermissionsPage() {
  const [modulos, setModulos] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    permissionsService.catalog()
      .then((data) => setModulos(data.modules))
      .catch(() => setError('No se pudo cargar el catálogo de permisos.'))
  }, [])

  return (
    <div>
      <div className="mz-view-head">
        <div>
          <h2>Catálogo de permisos</h2>
          <p className="mz-desc">
            Solo lectura: los permisos están definidos en el código del sistema, no se editan aquí.
          </p>
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}
      {!modulos && !error && <div className="text-center py-3" role="status" aria-live="polite"><Spinner animation="border" size="sm" /></div>}

      {modulos && Object.entries(modulos).map(([modulo, permisos]) => (
        <section key={modulo} className="mz-card mb-3">
          <div className="mz-card-head"><h3 className="text-capitalize">{modulo}</h3></div>
          <div>
            <Table responsive size="sm" className="mb-0">
              <thead>
                <tr><th>Código</th><th>Descripción</th></tr>
              </thead>
              <tbody>
                {permisos.map((p) => (
                  <tr key={p.codename}>
                    <td className="mz-code">{p.codename}</td>
                    <td>{p.name}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </section>
      ))}
    </div>
  )
}
