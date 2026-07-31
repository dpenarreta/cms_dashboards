import { Table } from 'react-bootstrap'
import Pagination from '../common/Pagination'
import { useDrilldown } from '../../hooks/useDrilldown'
import { usePaginacionCliente } from '../../hooks/usePaginacionCliente'
import { formatCurrency, formatNumber, formatPercent } from '../../utils/format'

function CeldaSeleccionable({ onSeleccionar, children }) {
  return (
    <td
      role="button"
      tabIndex={0}
      onClick={onSeleccionar}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSeleccionar() } }}
      style={{ cursor: 'pointer' }}
    >
      {children}
    </td>
  )
}

export default function RecuperadorCausalMatrix({ matriz, metrica, override }) {
  const { abrirDetalle } = useDrilldown()
  const {
    pagina, pageSize, totalPaginas, totalRegistros, itemsPagina: filasPaginadas, irAPagina, cambiarPageSize,
  } = usePaginacionCliente(matriz?.filas, { defaultPageSize: override?.config?.defaultPageSize ?? 10, resetKey: matriz })

  if (!matriz || matriz.filas.length === 0) return null

  const formatear = (v) => (metrica === 'saldo' ? formatCurrency(v || 0) : formatNumber(v || 0))

  const seleccionarCelda = (recuperador, causal) => abrirDetalle({
    origen: 'matriz_recuperador_causal',
    titulo: `${recuperador} — ${causal}`,
    filtros: { recuperador, causal },
  })

  const seleccionarFila = (recuperador) => abrirDetalle({
    origen: 'matriz_recuperador_causal',
    titulo: `Cartera de ${recuperador}`,
    filtros: { recuperador },
  })

  const seleccionarColumna = (causal) => abrirDetalle({
    origen: 'matriz_recuperador_causal',
    titulo: `Cartera con causal ${causal}`,
    filtros: { causal },
  })

  return (
    <div className="chart-panel">
      <div className="chart-panel__title">{override?.titulo || 'Matriz de recuperadores y causales'}</div>
      <div className="chart-panel__subtitle">{override?.descripcion || 'Totales por fila/columna y % de cartera gestionada por recuperador. Cualquier celda o total es seleccionable.'}</div>
      <div className="table-scroll">
        <Table size="sm" bordered className="matrix-table">
          <thead>
            <tr>
              <th>Recuperador</th>
              {matriz.columnas.map((c) => <th key={c}>{c}</th>)}
              <th>Total</th>
              <th>% gestionado</th>
              <th>% sin gestión</th>
            </tr>
          </thead>
          <tbody>
            {filasPaginadas.map((recuperador) => (
              <tr key={recuperador}>
                <td>{recuperador}</td>
                {matriz.columnas.map((causal) => (
                  <CeldaSeleccionable key={causal} onSeleccionar={() => seleccionarCelda(recuperador, causal)}>
                    {formatear(matriz.celdas[recuperador]?.[causal])}
                  </CeldaSeleccionable>
                ))}
                <CeldaSeleccionable onSeleccionar={() => seleccionarFila(recuperador)}>
                  <strong>{formatear(matriz.totales_fila[recuperador])}</strong>
                </CeldaSeleccionable>
                <td>{formatPercent(matriz.porcentajes_gestion[recuperador]?.porcentaje_gestionado)}</td>
                <td>{formatPercent(matriz.porcentajes_gestion[recuperador]?.porcentaje_sin_gestion)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th>Total por causal</th>
              {matriz.columnas.map((c) => (
                <CeldaSeleccionable key={c} onSeleccionar={() => seleccionarColumna(c)}>
                  {formatear(matriz.totales_columna[c])}
                </CeldaSeleccionable>
              ))}
              <th>{formatear(matriz.total_general)}</th>
              <th colSpan={2} />
            </tr>
          </tfoot>
        </Table>
      </div>
      <Pagination
        idBase="matriz-recuperador-causal"
        paginaActual={pagina}
        totalPaginas={totalPaginas}
        totalRegistros={totalRegistros}
        pageSize={pageSize}
        allowedPageSizes={override?.config?.allowedPageSizes || [5, 10, 25, 50, 100]}
        onCambiarPagina={irAPagina}
        onCambiarPageSize={cambiarPageSize}
      />
    </div>
  )
}
