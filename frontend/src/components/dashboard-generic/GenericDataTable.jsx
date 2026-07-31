import { Table } from 'react-bootstrap'
import { formatNumber } from '../../utils/format'

/**
 * Renderiza un componente type=chart de una sola serie (`{titulo, categorias, valores}`) como una
 * tabla simple de dos columnas — ya viene acotada a lo sumo a 16 filas (15 + "Otras", ver
 * `services/generic_charts.py::_agrupar_top_n`), no necesita paginación.
 */
export default function GenericDataTable({ data, override }) {
  if (!data) return null
  const filas = (data.categorias || []).map((categoria, i) => ({ categoria, valor: data.valores?.[i] ?? 0 }))

  return (
    <div className="chart-panel" style={override?.colores?.colorFondo ? { background: override.colores.colorFondo } : undefined}>
      <div className="chart-panel__title" style={override?.colores?.colorTexto ? { color: override.colores.colorTexto } : undefined}>
        {override?.titulo || data.titulo}
      </div>
      {(override?.descripcion || data.descripcion) && (
        <div className="chart-panel__subtitle">{override?.descripcion || data.descripcion}</div>
      )}
      <Table responsive size="sm" className="mb-0">
        <thead>
          <tr>
            <th>Categoría</th>
            <th className="text-end">Valor</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((fila) => (
            <tr key={fila.categoria}>
              <td>{fila.categoria}</td>
              <td className="text-end">{formatNumber(fila.valor)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  )
}
