import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Alert, Button, Form, Modal, Spinner, Table } from 'react-bootstrap'
import * as historicoService from '../../services/historicoService'
import * as carteraService from '../../services/carteraService'
import ConfirmModal from '../../components/dashboard-editor/ConfirmModal'
import GenericDataTable from '../../components/dashboard-generic/GenericDataTable'
import { SelectorColumna, SelectorTipoAgregacion, normalizarColumnaValorTabla } from '../../components/dashboard-generic/SlotFields'
import { formatDate, formatNumber } from '../../utils/format'

/**
 * Histórico de archivos cargados (sección 28): cada archivo aplicado a la plantilla de un
 * dashboard (`AplicarMapeoPlantillaView`) queda guardado fila por fila
 * (`FilaArchivoHistorico`, ligado a su `CargaArchivo` de origen — se borra en cascada si esa
 * carga se elimina). Acá se eligen cuáles cargas incluir y qué columnas comparar (cada una con su
 * propio tipo de cálculo, igual que una tabla normal del dashboard) para armar una tabla con una
 * fila por carga — reutiliza `GenericDataTable` tal cual para mostrarla (orden y paginación salen
 * gratis; `mostrarHallazgos={false}` en ambos usos de esta página, tanto la tabla histórica
 * generada como el modal "Ver archivo": acá se está comparando/previsualizando el dato crudo, no
 * pidiendo una interpretación).
 */
export default function DashboardHistoricoPage() {
  const { dashboardId } = useParams()
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState('')
  const [cargas, setCargas] = useState([])
  const [columnasDisponibles, setColumnasDisponibles] = useState([])
  const [seleccionadas, setSeleccionadas] = useState(new Set())
  const [columnasValor, setColumnasValor] = useState([])
  const [tabla, setTabla] = useState(null)
  const [generando, setGenerando] = useState(false)
  const [errorTabla, setErrorTabla] = useState('')
  const [cargaAEliminar, setCargaAEliminar] = useState(null)
  const [eliminando, setEliminando] = useState(false)
  const [cargaAVer, setCargaAVer] = useState(null)
  const [archivoVisto, setArchivoVisto] = useState(null)
  const [cargandoArchivo, setCargandoArchivo] = useState(false)
  const [errorArchivo, setErrorArchivo] = useState('')

  const cargar = () => {
    setCargando(true)
    setError('')
    historicoService.listarCargasHistoricas(dashboardId)
      .then((resultado) => {
        setCargas(resultado.cargas)
        setColumnasDisponibles(resultado.columnas_disponibles)
        setSeleccionadas(new Set(resultado.cargas.map((c) => c.carga_id)))
      })
      .catch(() => setError('No se pudo cargar el histórico de este dashboard.'))
      .finally(() => setCargando(false))
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps -- solo debe recargar cuando cambia el dashboard
  useEffect(cargar, [dashboardId])

  const alternarCarga = (cargaId) => {
    setSeleccionadas((prev) => {
      const siguiente = new Set(prev)
      if (siguiente.has(cargaId)) siguiente.delete(cargaId)
      else siguiente.add(cargaId)
      return siguiente
    })
  }

  const opcionesColumna = columnasDisponibles.map((nombre) => ({ nombre }))
  const lista = columnasValor.length > 0 ? columnasValor : [normalizarColumnaValorTabla(null)]

  const cambiarColumna = (i) => (valor) => {
    const nueva = [...lista]
    nueva[i] = { ...normalizarColumnaValorTabla(nueva[i]), columna: valor }
    setColumnasValor(nueva)
  }
  const cambiarAgregacion = (i) => (valor) => {
    const nueva = [...lista]
    nueva[i] = { ...normalizarColumnaValorTabla(nueva[i]), tipo_agregacion: valor }
    setColumnasValor(nueva)
  }
  const agregarColumna = () => setColumnasValor([...lista, normalizarColumnaValorTabla(null)])
  const quitarColumna = (i) => setColumnasValor(lista.filter((_, idx) => idx !== i))

  const generarTabla = async () => {
    const columnasElegidas = lista.filter((c) => c.columna)
    if (columnasElegidas.length === 0) {
      setErrorTabla('Elegí al menos una columna para comparar.')
      return
    }
    setErrorTabla('')
    setGenerando(true)
    try {
      const resultado = await historicoService.calcularTablaHistorica(dashboardId, columnasElegidas, [...seleccionadas])
      setTabla(resultado)
    } catch {
      setErrorTabla('No se pudo generar la tabla histórica.')
    } finally {
      setGenerando(false)
    }
  }

  const verArchivo = (carga) => {
    setCargaAVer(carga)
    setArchivoVisto(null)
    setErrorArchivo('')
    setCargandoArchivo(true)
    historicoService.obtenerArchivoCarga(carga.carga_id)
      .then(setArchivoVisto)
      .catch(() => setErrorArchivo('No se pudo cargar el archivo.'))
      .finally(() => setCargandoArchivo(false))
  }

  const confirmarEliminar = async () => {
    setEliminando(true)
    try {
      await carteraService.eliminarArchivo(cargaAEliminar.carga_id)
      setCargaAEliminar(null)
      setTabla(null)
      cargar()
    } finally {
      setEliminando(false)
    }
  }

  return (
    <div className="cartera-app">
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-4">
        <div>
          <h3 className="mb-1">Histórico de cargas</h3>
          <p className="chart-panel__subtitle mb-0">
            Compará la evolución de una o más columnas a través de las cargas de este dashboard.
          </p>
        </div>
        <Button as={Link} to={`/app/dashboards/${dashboardId}`} variant="outline-secondary" size="sm">
          Volver al dashboard
        </Button>
      </div>

      {cargando && <div className="text-center mb-3" role="status"><Spinner animation="border" /></div>}
      {!cargando && error && <Alert variant="danger">{error}</Alert>}

      {!cargando && !error && cargas.length === 0 && (
        <Alert variant="secondary">
          Todavía no hay cargas históricas para este dashboard. Subí y aplicá un archivo (botón
          "Cargar otro archivo") para empezar a construir el histórico.
        </Alert>
      )}

      {!cargando && !error && cargas.length > 0 && (
        <>
          <div className="chart-panel mb-3">
            <div className="chart-panel__title">Cargas disponibles</div>
            <Table responsive size="sm" className="mb-0">
              <thead>
                <tr>
                  <th aria-label="Incluir" />
                  <th>Archivo</th>
                  <th>Fecha de carga</th>
                  <th>Fecha de corte</th>
                  <th className="text-end">Filas</th>
                  <th aria-label="Acciones" />
                </tr>
              </thead>
              <tbody>
                {cargas.map((carga) => (
                  <tr key={carga.carga_id}>
                    <td>
                      <Form.Check
                        type="checkbox"
                        checked={seleccionadas.has(carga.carga_id)}
                        onChange={() => alternarCarga(carga.carga_id)}
                        aria-label={`Incluir ${carga.nombre_original}`}
                      />
                    </td>
                    <td>{carga.nombre_original}</td>
                    <td>{formatDate(carga.fecha_carga.slice(0, 10))}</td>
                    <td>{carga.fecha_corte ? formatDate(carga.fecha_corte) : '—'}</td>
                    <td className="text-end">{formatNumber(carga.total_filas)}</td>
                    <td className="d-flex gap-2">
                      <Button size="sm" variant="outline-secondary" onClick={() => verArchivo(carga)}>
                        Ver archivo
                      </Button>
                      <Button size="sm" variant="outline-danger" onClick={() => setCargaAEliminar(carga)}>
                        Eliminar
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>

          <div className="chart-panel mb-3">
            <div className="chart-panel__title mb-2">Columnas a comparar</div>
            {lista.map((fila, i) => (
              <div key={i} className="mb-2 p-2 border rounded">
                <SelectorColumna
                  etiqueta={`Columna ${i + 1}`} contexto="histórico" valor={fila.columna} opciones={opcionesColumna}
                  onCambiar={cambiarColumna(i)}
                />
                <SelectorTipoAgregacion contexto={`columna ${i + 1} del histórico`} valor={fila.tipo_agregacion} onCambiar={cambiarAgregacion(i)} />
                <Button size="sm" variant="outline-danger" onClick={() => quitarColumna(i)} disabled={lista.length <= 1}>
                  Quitar columna
                </Button>
              </div>
            ))}
            <div className="d-flex gap-2 align-items-center flex-wrap">
              <Button size="sm" variant="outline-secondary" onClick={agregarColumna}>+ Agregar columna</Button>
              <Button size="sm" variant="primary" onClick={generarTabla} disabled={generando}>
                {generando ? 'Generando…' : 'Generar tabla histórica'}
              </Button>
            </div>
            {errorTabla && <Alert variant="danger" className="mt-2 mb-0 py-2">{errorTabla}</Alert>}
          </div>

          {tabla && (
            <GenericDataTable
              data={{ titulo: 'Tabla histórica', columnas: tabla.columnas, filas: tabla.filas }}
              mostrarHallazgos={false}
            />
          )}
        </>
      )}

      <ConfirmModal
        show={Boolean(cargaAEliminar)}
        title="Eliminar carga histórica"
        confirmLabel={eliminando ? 'Eliminando…' : 'Eliminar'}
        onConfirm={confirmarEliminar}
        onCancel={() => setCargaAEliminar(null)}
      >
        {cargaAEliminar && (
          <Alert variant="warning" className="mb-0">
            Se eliminará "{cargaAEliminar.nombre_original}" y todas sus filas históricas. No se puede deshacer.
          </Alert>
        )}
      </ConfirmModal>

      <Modal show={Boolean(cargaAVer)} onHide={() => setCargaAVer(null)} size="xl" centered scrollable>
        <Modal.Header closeButton>
          <Modal.Title>{cargaAVer?.nombre_original}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {cargandoArchivo && <div className="text-center py-3" role="status"><Spinner animation="border" /></div>}
          {!cargandoArchivo && errorArchivo && <Alert variant="danger">{errorArchivo}</Alert>}
          {!cargandoArchivo && !errorArchivo && archivoVisto && (
            archivoVisto.filas.length > 0
              ? (
                <GenericDataTable
                  data={{ titulo: cargaAVer?.nombre_original, columnas: archivoVisto.columnas, filas: archivoVisto.filas }}
                  mostrarHallazgos={false}
                />
              )
              : <Alert variant="secondary" className="mb-0">Este archivo no tiene filas guardadas.</Alert>
          )}
        </Modal.Body>
      </Modal>
    </div>
  )
}
