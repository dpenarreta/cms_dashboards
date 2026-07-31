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
      <h1 className="h4 mb-3">Catálogo de permisos</h1>
      <p className="chart-panel__subtitle">
        Solo lectura: los permisos están definidos en el código del sistema, no se editan aquí.
      </p>

      {error && <Alert variant="danger">{error}</Alert>}
      {!modulos && !error && <div className="text-center py-3" role="status" aria-live="polite"><Spinner animation="border" size="sm" /></div>}

      {modulos && Object.entries(modulos).map(([modulo, permisos]) => (
        <div key={modulo} className="mb-4">
          <h6 className="text-capitalize">{modulo}</h6>
          <div className="table-scroll">
            <Table size="sm" striped bordered>
              <thead>
                <tr><th>Código</th><th>Descripción</th></tr>
              </thead>
              <tbody>
                {permisos.map((p) => (
                  <tr key={p.codename}>
                    <td><code>{p.codename}</code></td>
                    <td>{p.name}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        </div>
      ))}
    </div>
  )
}
