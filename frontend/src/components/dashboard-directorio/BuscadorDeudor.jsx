import { useState } from 'react'
import { buscarDeudores, obtenerDetalleDeudor } from '../../services/dashboardLayoutService'
import { TituloSeccion } from './comunes'
import { moneda, porcentaje } from './formato'

/**
 * Consulta puntual de un deudor: antigüedad a la izquierda, sus documentos a la derecha.
 *
 * Las otras secciones del informe muestran a los clientes más grandes; ninguna deja preguntar por
 * uno en particular. Acá se escribe un nombre o un identificador, se elige entre las coincidencias
 * y se ven sus seis tramos más las filas del archivo donde aparece.
 *
 * Por qué se elige entre coincidencias en vez de sumarlas: un texto corto ("transex") puede tocar
 * dos razones sociales distintas, y sumarlas daría un total que no le corresponde a ninguna. El
 * backend devuelve las coincidencias con su saldo justamente para poder distinguirlas antes.
 *
 * Qué columnas trae el detalle lo decide `config.columnas_detalle` del componente —o sea, quien
 * arma el dashboard— y no cada usuario: es parte de la configuración que se guarda y se ve igual
 * para todos.
 */
export default function BuscadorDeudor({ componente, dashboardId }) {
  const { content, mapeo, config } = componente
  const [texto, setTexto] = useState('')
  const [coincidencias, setCoincidencias] = useState(null)
  const [detalle, setDetalle] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  // El dashboard llega por prop desde la página (que lo tiene de la ruta) y no desde `config`:
  // es una propiedad de DÓNDE está montado el componente, no de cómo está configurado, y meterlo
  // en la configuración guardada lo dejaría apuntando al dashboard equivocado si alguien
  // duplicara el componente en otro.
  const columnas = {
    nombre: mapeo?.columna_id,
    ruc: mapeo?.columna_ruc,
    fecha: mapeo?.columna_fecha,
    valor: mapeo?.columna_valor,
  }

  function buscar(evento) {
    evento?.preventDefault()
    if (!texto.trim()) return
    setCargando(true)
    setError('')
    setDetalle(null)
    buscarDeudores(dashboardId, { texto: texto.trim(), columnas })
      .then((datos) => {
        setCoincidencias(datos.coincidencias)
        // Con una sola coincidencia, elegirla a mano es un clic sin decisión: se abre directo.
        if (datos.coincidencias.length === 1) elegir(datos.coincidencias[0].identidad)
      })
      .catch((e) => setError(e.response?.data?.mensaje || 'No se pudo completar la búsqueda.'))
      .finally(() => setCargando(false))
  }

  function elegir(identidad) {
    setCargando(true)
    setError('')
    obtenerDetalleDeudor(dashboardId, {
      identidad, columnas, columnasDetalle: config?.columnas_detalle,
    })
      .then(setDetalle)
      .catch((e) => setError(e.response?.data?.mensaje || 'No se pudo traer el detalle.'))
      .finally(() => setCargando(false))
  }

  return (
    <div className="chart-panel directorio-seccion">
      <TituloSeccion>{content?.titulo || 'CONSULTA POR CLIENTE'}</TituloSeccion>

      <form className="directorio-buscador" onSubmit={buscar}>
        <input
          type="search"
          className="form-control"
          placeholder="Nombre o identificador del cliente"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          aria-label="Nombre o identificador del cliente"
        />
        <button type="submit" className="btn btn-primary" disabled={cargando || !texto.trim()}>
          {cargando ? 'Consultando…' : 'Consultar'}
        </button>
      </form>

      {error && <div className="alert alert-warning py-2 mb-3">{error}</div>}

      {/* La lista solo aparece cuando hay algo que decidir: con una coincidencia se abrió sola. */}
      {coincidencias && coincidencias.length > 1 && !detalle && (
        <div className="directorio-coincidencias">
          <div className="directorio-coincidencias__titulo">
            {coincidencias.length} coincidencias — elegí una:
          </div>
          {coincidencias.map((c) => (
            <button key={c.identidad} type="button" className="directorio-coincidencia" onClick={() => elegir(c.identidad)}>
              <span className="directorio-coincidencia__nombre">{c.nombre}</span>
              <span className="directorio-coincidencia__id">{c.identidad}</span>
              <span className="directorio-coincidencia__saldo">{moneda(c.saldo)}</span>
              <span className="directorio-coincidencia__filas">{c.filas} fila{c.filas === 1 ? '' : 's'}</span>
            </button>
          ))}
        </div>
      )}

      {coincidencias && coincidencias.length === 0 && !cargando && (
        <p className="text-muted mb-0">No hay clientes que coincidan con «{texto}».</p>
      )}

      {detalle && <ResultadoDeudor detalle={detalle} onVolver={() => setDetalle(null)}
                                   hayVarias={(coincidencias?.length || 0) > 1} />}
    </div>
  )
}

function ResultadoDeudor({ detalle, onVolver, hayVarias }) {
  const { tramos, filas, columnas } = detalle
  const total = detalle.total || 0

  return (
    <div className="directorio-deudor-consulta">
      <div className="directorio-deudor-consulta__encabezado">
        <div className="directorio-deudor__titulo">
          {detalle.nombre} — {moneda(total)} · {detalle.cantidad_filas} documento
          {detalle.cantidad_filas === 1 ? '' : 's'}
        </div>
        {hayVarias && (
          <button type="button" className="btn btn-link btn-sm p-0" onClick={onVolver}>
            ← Elegir otro cliente
          </button>
        )}
      </div>

      <div className="directorio-deudor-consulta__cuerpo">
        <div className="directorio-deudor-consulta__antiguedad">
          <table className="directorio-tabla directorio-tabla--compacta">
            <thead>
              <tr>
                <th>TRAMO</th>
                <th className="text-end">SALDO</th>
                <th className="text-end">%</th>
              </tr>
            </thead>
            <tbody>
              {(tramos?.categorias || []).map((categoria, i) => {
                const valor = tramos.valores[i] ?? 0
                return (
                  <tr key={categoria}>
                    <td>{categoria}</td>
                    <td className="text-end">{moneda(valor)}</td>
                    {/* Un tramo sin filas muestra 0, no se oculta: que esté vacío es información. */}
                    <td className="text-end">{porcentaje(total ? (valor / total) * 100 : 0)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="directorio-deudor-consulta__detalle">
          <div className="directorio-tabla-scroll">
            <table className="directorio-tabla directorio-tabla--compacta">
              <thead>
                <tr>
                  {columnas.map((columna) => (
                    <th key={columna}>{String(columna).toUpperCase()}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filas.map((fila, i) => (
                  // eslint-disable-next-line react/no-array-index-key -- dos documentos pueden ser idénticos
                  <tr key={i}>
                    {fila.map((valor, j) => (
                      // eslint-disable-next-line react/no-array-index-key -- la columna puede repetirse
                      <td key={j}>{valor === null || valor === undefined ? '—' : String(valor)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
