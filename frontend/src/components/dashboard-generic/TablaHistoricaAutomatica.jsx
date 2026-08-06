import { useEffect, useState } from 'react'
import { Spinner } from 'react-bootstrap'
import * as historicoService from '../../services/historicoService'
import GenericDataTable from './GenericDataTable'

/**
 * Tabla 4 y Tabla 5 de la plantilla fija: a diferencia del resto de posiciones (una foto fija,
 * calculada una sola vez al aplicar el mapeo de un archivo), estas consultan en vivo la tabla
 * histórica comparativa entre TODAS las cargas del dashboard (una fila por carga, las mismas
 * columnas de valor que se mapearon para esta posición) cada vez que se ve el dashboard — así
 * reflejan archivos subidos después de la última vez que se aplicó el mapeo, sin tener que volver
 * a aplicarlo. Reutiliza los mismos endpoints que "Ver histórico" (`historicoService`) y el mismo
 * `GenericDataTable` para dibujar el resultado (orden, paginación y hallazgos clave incluidos).
 * Todo lo que este componente renderiza directamente ES la comparación histórica, así que siempre
 * lleva la etiqueta fija "Histórica" (`esHistorica`, ver `GenericDataTable`).
 *
 * Si todavía no hay ninguna carga histórica para el dashboard, o esta posición nunca se mapeó a
 * ninguna columna de valor (dashboard nuevo, con dato ficticio), cae a `contenidoNormal` — no hay
 * nada que comparar todavía.
 */
export default function TablaHistoricaAutomatica({ dashboardId, columnasValor, override, contenidoNormal }) {
  const columnasValidas = (columnasValor || []).filter((c) => c?.columna)
  const claveColumnas = JSON.stringify(columnasValidas)

  const [tabla, setTabla] = useState(null)
  const [cargando, setCargando] = useState(columnasValidas.length > 0)

  useEffect(() => {
    if (columnasValidas.length === 0) {
      setTabla(null)
      setCargando(false)
      return undefined
    }

    let cancelado = false
    setCargando(true)
    historicoService.listarCargasHistoricas(dashboardId)
      .then((resultado) => (
        resultado.cargas.length > 0
          ? historicoService.calcularTablaHistorica(dashboardId, columnasValidas)
          : null
      ))
      .then((resultado) => { if (!cancelado) setTabla(resultado) })
      .catch(() => { if (!cancelado) setTabla(null) })
      .finally(() => { if (!cancelado) setCargando(false) })
    return () => { cancelado = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- las columnas se comparan por su versión serializada (claveColumnas)
  }, [dashboardId, claveColumnas])

  if (cargando) {
    return (
      <div className="chart-panel text-center py-4">
        <Spinner animation="border" size="sm" role="status" />
      </div>
    )
  }

  if (tabla) {
    return (
      <GenericDataTable
        data={{ titulo: override?.titulo, descripcion: override?.descripcion, columnas: tabla.columnas, filas: tabla.filas }}
        override={override}
        esHistorica
      />
    )
  }

  return contenidoNormal
}
