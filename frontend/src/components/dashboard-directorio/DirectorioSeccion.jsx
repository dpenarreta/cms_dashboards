import {
  Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { HallazgosClave, Nota, TituloSeccion } from './comunes'
import { moneda, porcentaje } from './formato'

/**
 * Renderers a medida del Dashboard Directorio — réplica de la pestaña "6. Cartera" de un informe
 * financiero mensual.
 *
 * Existen porque los componentes genéricos no saben dibujar lo que ese informe muestra: etiquetas
 * con monto y porcentaje SOBRE cada barra, una tabla con la meta al lado del valor y una marca
 * ✓/✗, dos tarjetas resumen dentro de una sección, y mini-tablas por deudor una al lado de la
 * otra. Extender los genéricos para cubrir esto los volvería un cajón de sastre y afectaría a
 * todos los dashboards; acá el alcance es exactamente un dashboard.
 *
 * El despacho es por `content.bloque`, que arma `services/directorio_cartera.py`. Un bloque
 * desconocido no rompe la pantalla: no dibuja nada.
 */

function TarjetaKpi({ data }) {
  return (
    <div className="directorio-kpi" style={{ borderLeftColor: data.color }}>
      <div className="directorio-kpi__etiqueta">{data.etiqueta}</div>
      <div className="directorio-kpi__valor">{moneda(data.valor)}</div>
      <div className={`directorio-kpi__sub directorio-kpi__sub--${data.tono || 'neutro'}`}>
        {data.subtitulo}
      </div>
    </div>
  )
}

function GraficoAntiguedad({ data }) {
  const filas = (data.categorias || []).map((categoria, i) => ({
    categoria,
    valor: data.valores?.[i] ?? 0,
    etiqueta: data.etiquetas?.[i] ?? '',
    color: data.colores?.[i],
  }))

  return (
    <div className="chart-panel directorio-seccion">
      <TituloSeccion>{data.titulo}</TituloSeccion>
      <ResponsiveContainer width="100%" height={300}>
        {/* `top: 28` deja aire para la etiqueta que va encima de la barra más alta; sin eso
            recharts la recorta contra el borde del gráfico. */}
        <BarChart data={filas} margin={{ left: 8, right: 16, top: 28, bottom: 8 }}>
          <CartesianGrid horizontal vertical={false} stroke="var(--border)" />
          <XAxis dataKey="categoria" interval={0} tick={{ fontSize: 12 }} />
          <YAxis width={76} tick={{ fontSize: 11 }} tickFormatter={(v) => `$${Math.round(v / 1000)}K`} />
          <Tooltip formatter={(valor) => moneda(valor)} />
          <Bar dataKey="valor" radius={[3, 3, 0, 0]} maxBarSize={64}>
            <LabelList dataKey="etiqueta" position="top" className="directorio-barra__etiqueta" />
            {filas.map((fila) => <Cell key={fila.categoria} fill={fila.color} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <HallazgosClave texto={data.hallazgos} />
    </div>
  )
}

function TablaCumplimiento({ data }) {
  return (
    <div className="chart-panel directorio-seccion">
      <TituloSeccion>{data.titulo}</TituloSeccion>
      <table className="directorio-tabla">
        <thead>
          <tr>
            {data.columnas.map((columna, i) => (
              // eslint-disable-next-line react/no-array-index-key -- encabezados fijos de la sección
              <th key={i} className={i === 0 ? undefined : 'text-end'}>{columna}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.filas.map((fila) => (
            <tr key={fila.edad} className={fila.es_cola ? 'directorio-tabla__fila--cierre' : undefined}>
              <td>{fila.edad}</td>
              <td className="text-end directorio-tabla__meta">{fila.meta}</td>
              <td className="text-end">{moneda(fila.valor)}</td>
              <td className={`text-end ${fila.cumple ? 'directorio-ok' : 'directorio-falla'}`}>
                {porcentaje(fila.porcentaje)} {fila.cumple ? '✓' : '✗'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Nota texto={data.nota} />
    </div>
  )
}

function SeccionConcentracion({ data }) {
  return (
    <div className="chart-panel directorio-seccion">
      <TituloSeccion>{data.titulo}</TituloSeccion>
      <div className="directorio-resumen">
        {data.resumen.map((tarjeta) => (
          <div key={tarjeta.etiqueta} className="directorio-kpi directorio-kpi--interno" style={{ borderLeftColor: tarjeta.color }}>
            <div className="directorio-kpi__etiqueta">{tarjeta.etiqueta}</div>
            <div className="directorio-kpi__valor">{moneda(tarjeta.valor)}</div>
            <div className="directorio-kpi__sub directorio-kpi__sub--neutro">{tarjeta.subtitulo}</div>
          </div>
        ))}
      </div>
      <table className="directorio-tabla">
        <thead>
          <tr>
            {data.columnas.map((columna, i) => (
              // eslint-disable-next-line react/no-array-index-key -- encabezados fijos de la sección
              <th key={i} className={i === 0 ? undefined : 'text-end'}>{columna}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.filas.map(([cliente, saldo, pct, acumulado]) => (
            <tr key={cliente}>
              <td>{cliente}</td>
              <td className="text-end">{moneda(saldo)}</td>
              <td className="text-end">{porcentaje(pct, 2)}</td>
              <td className="text-end">{porcentaje(acumulado, 2)}</td>
            </tr>
          ))}
          <tr className="directorio-tabla__fila--resto">
            <td>{data.fila_resto[0]}</td>
            <td className="text-end">{moneda(data.fila_resto[1])}</td>
            <td className="text-end">{porcentaje(data.fila_resto[2], 2)}</td>
            <td className="text-end">{porcentaje(data.fila_resto[3], 2)}</td>
          </tr>
          <tr className="directorio-tabla__fila--total">
            <td>{data.fila_total[0]}</td>
            <td className="text-end">{moneda(data.fila_total[1])}</td>
            <td className="text-end">{porcentaje(data.fila_total[2], 2)}</td>
            <td className="text-end">—</td>
          </tr>
        </tbody>
      </table>
      <HallazgosClave texto={data.hallazgos} />
      <Nota texto={data.nota} />
    </div>
  )
}

function SeccionDeudores({ data }) {
  return (
    <div className="chart-panel directorio-seccion">
      <TituloSeccion>{data.titulo}</TituloSeccion>
      <div className="directorio-deudores">
        {data.deudores.map((deudor) => (
          <div key={deudor.nombre} className="directorio-deudor">
            <div className="directorio-deudor__titulo">
              {deudor.nombre} — {moneda(deudor.saldo)} ({porcentaje(deudor.porcentaje_cartera, 2)} de la cartera total)
            </div>
            <table className="directorio-tabla directorio-tabla--compacta">
              <thead>
                <tr>
                  {deudor.columnas.map((columna, i) => (
                    // eslint-disable-next-line react/no-array-index-key -- encabezados fijos
                    <th key={i} className={i === 0 ? undefined : 'text-end'}>{columna}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deudor.filas.map((fila) => (
                  <tr
                    key={fila.tramo}
                    className={fila.tramo === deudor.tramo_destacado ? 'directorio-tabla__fila--destacada' : undefined}
                  >
                    <td>{fila.tramo}</td>
                    <td className="text-end">{moneda(fila.saldo)}</td>
                    <td className="text-end">{porcentaje(fila.porcentaje)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="directorio-deudor__comentario">{deudor.comentario}</p>
          </div>
        ))}
      </div>
      <HallazgosClave texto={data.hallazgos} />
      <Nota texto={data.fuente} />
    </div>
  )
}

const POR_BLOQUE = {
  kpi: TarjetaKpi,
  antiguedad: GraficoAntiguedad,
  cumplimiento: TablaCumplimiento,
  concentracion: SeccionConcentracion,
  deudores: SeccionDeudores,
}

export default function DirectorioSeccion({ content }) {
  const Componente = POR_BLOQUE[content?.bloque]
  return Componente ? <Componente data={content} /> : null
}
