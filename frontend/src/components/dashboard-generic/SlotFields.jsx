import { useEffect, useState } from 'react'
import { Button, Form } from 'react-bootstrap'
import * as carteraService from '../../services/carteraService'
import { ETIQUETAS_TIPO_VISUALIZACION, TIPOS_COMPATIBLES } from '../../utils/plantillaSlots'

/**
 * Piezas de selección de mapeo (columna/tipo de cálculo/tipo de gráfico/filtro) de una posición
 * de la plantilla fija — compartidas entre el paso de mapeo inicial (`TemplateMappingStep`, tras
 * cargar un archivo) y la sección "Datos" del panel de "Configurar componente"
 * (`ComponentDataSection`, para reconfigurar una posición ya aplicada). Un mismo criterio en un
 * solo lugar evita que ambos flujos diverjan en cómo arman/leen la propuesta de mapeo.
 */

/** El tipo de gráfico que de verdad se dibuja para una posición: el que el usuario eligió si es
 * compatible con el `calculo` de la posición (mismos datos calculados), o el tipo por defecto del
 * slot en cualquier otro caso — mismo criterio que `services/plantilla.py::_chart_type_elegido`. */
export function tipoVisualizacionElegido(slot, propuesta) {
  const compatibles = TIPOS_COMPATIBLES[slot.calculo]
  if (compatibles && compatibles.includes(propuesta.chart_type)) return propuesta.chart_type
  return slot.tipoVisualizacion
}

/** `datos[slot.id]` (calculado por el backend) viene como `{categorias, valores}` o
 * `{categorias, series}` según el `calculo` de la posición — `GenericChartRenderer` espera esa
 * forma en `datos` o `datosMultiserie` según corresponda. */
export function datosParaPreview(slot, contenido) {
  if (!contenido) return {}
  if (slot.calculo === 'multivalor' || slot.calculo === 'multiserie') return { datosMultiserie: contenido }
  return { datos: contenido }
}

export function SelectorColumna({ etiqueta, contexto, valor, opciones, onCambiar }) {
  return (
    <Form.Group className="mb-2">
      <Form.Label className="mb-1" style={{ fontSize: '0.8rem' }}>{etiqueta}</Form.Label>
      <Form.Select
        size="sm"
        value={valor || ''}
        onChange={(e) => onCambiar(e.target.value || null)}
        aria-label={`${etiqueta} de ${contexto}`}
      >
        <option value="">Sin usar</option>
        {opciones.map((c) => <option key={c.nombre} value={c.nombre}>{c.nombre}</option>)}
      </Form.Select>
    </Form.Group>
  )
}

/** Compartido entre los KPI (un único valor) y cada columna de valor de una Tabla (sección 23,
 * una por columna — no aplica a la columna de "Identidad de fila"): "Suma" agrega los valores de
 * la columna (para montos/cantidades); "Promedio" calcula su media aritmética (para
 * montos/cantidades típicos, p. ej. saldo promedio); "Cantidad de valores únicos" cuenta cuántos
 * valores distintos tiene (para saber, p. ej., cuántos clientes o números de documento diferentes
 * hay, sin importar si la columna es numérica); "Ver valor de celda" (solo Tablas, sección 23bis)
 * no agrega nada — muestra el valor real de la columna cuando es el mismo en todas las filas
 * agrupadas (columnas que identifican algo y no varían, p. ej. "Zona" o "Ciudad" de un cliente).
 * `permitirValorCelda` (por defecto `true`) lo oculta en el contexto de KPI, donde no aplica: un
 * KPI no agrupa filas, así que "el mismo valor en todo el grupo" no tiene sentido ahí. */
export function SelectorTipoAgregacion({ contexto, valor, onCambiar, permitirValorCelda = true }) {
  return (
    <Form.Group className="mb-2">
      <Form.Label className="mb-1" style={{ fontSize: '0.8rem' }}>Tipo de cálculo</Form.Label>
      <Form.Select
        size="sm"
        value={valor || 'suma'}
        onChange={(e) => onCambiar(e.target.value)}
        aria-label={`Tipo de cálculo de ${contexto}`}
      >
        <option value="suma">Suma</option>
        <option value="promedio">Promedio</option>
        <option value="conteo_unicos">Cantidad de valores únicos</option>
        {permitirValorCelda && <option value="valor_celda">Ver valor de celda</option>}
      </Form.Select>
    </Form.Group>
  )
}

/** Solo aplica a Gráficos (no a KPI/dispersión/tabla, cuyo `calculo` solo se puede dibujar de una
 * forma): elegir entre los tipos de visualización compatibles con los datos ya calculados para
 * esta posición (p. ej. Gráfico 1 puede pasar de barras a líneas o pastel sin perder el
 * mapeo de columnas elegido). */
export function SelectorTipoGrafico({ contexto, calculo, valor, valorDefecto, onCambiar }) {
  const opciones = TIPOS_COMPATIBLES[calculo]
  if (!opciones) return null
  return (
    <Form.Group className="mb-2">
      <Form.Label className="mb-1" style={{ fontSize: '0.8rem' }}>Tipo de gráfico</Form.Label>
      <Form.Select
        size="sm"
        value={valor || valorDefecto}
        onChange={(e) => onCambiar(e.target.value)}
        aria-label={`Tipo de gráfico de ${contexto}`}
      >
        {opciones.map((tipo) => <option key={tipo} value={tipo}>{ETIQUETAS_TIPO_VISUALIZACION[tipo]}</option>)}
      </Form.Select>
    </Form.Group>
  )
}

/**
 * Filtro opcional de una posición (aplica igual para un KPI que para cualquier gráfica o tabla,
 * ver `services/plantilla.py::_aplicar_filtro_slot`): elegir una columna de filtro carga en vivo
 * sus valores distintos (`obtenerValoresColumnaPlantilla`) para el segundo selector — así el
 * usuario nunca escribe un valor a mano, elige uno que de verdad existe en el archivo.
 */
export function FiltroSlot({ contexto, cargaId, aliases, valoresBlancos, columnas, columnaFiltro, valorFiltro, onCambiarColumna, onCambiarValor }) {
  const [valores, setValores] = useState([])
  const [cargandoValores, setCargandoValores] = useState(false)

  useEffect(() => {
    if (!columnaFiltro || !cargaId) {
      setValores([])
      return undefined
    }
    let cancelado = false
    setCargandoValores(true)
    carteraService.obtenerValoresColumnaPlantilla(cargaId, columnaFiltro, aliases, valoresBlancos)
      .then((resultado) => { if (!cancelado) setValores(resultado.valores || []) })
      .catch(() => { if (!cancelado) setValores([]) })
      .finally(() => { if (!cancelado) setCargandoValores(false) })
    return () => { cancelado = true }
  }, [columnaFiltro, cargaId, aliases, valoresBlancos])

  return (
    <div className="mt-2 pt-2 border-top">
      <div className="chart-panel__subtitle mb-1">Filtro (opcional)</div>
      <SelectorColumna
        etiqueta="Columna de filtro" contexto={contexto} valor={columnaFiltro} opciones={columnas}
        onCambiar={onCambiarColumna}
      />
      {columnaFiltro && (
        <Form.Group className="mb-2">
          <Form.Label className="mb-1" style={{ fontSize: '0.8rem' }}>Valor</Form.Label>
          <Form.Select
            size="sm"
            value={valorFiltro || ''}
            onChange={(e) => onCambiarValor(e.target.value || null)}
            aria-label={`Valor de filtro de ${contexto}`}
            disabled={cargandoValores}
          >
            <option value="">{cargandoValores ? 'Cargando valores…' : 'Todos'}</option>
            {valores.map((v) => <option key={v} value={v}>{v}</option>)}
          </Form.Select>
        </Form.Group>
      )}
    </div>
  )
}

/** Cada entrada de `columnas_valor` de una Tabla es `{columna, tipo_agregacion}` — también acepta
 * el string plano (o `null`) de antes de la sección 23, tratado como columna sin elegir o con
 * agregación "suma", para que una tabla ya mapeada antes de este cambio se siga editando sin
 * perder su selección. Compartida por `ColumnasTabla` y por quien arma los cambios de la lista
 * (`camposParaSlot`), así ambos coinciden en la forma normalizada. */
export function normalizarColumnaValorTabla(entrada) {
  if (entrada == null) return { columna: null, tipo_agregacion: 'suma' }
  if (typeof entrada === 'string') return { columna: entrada, tipo_agregacion: 'suma' }
  return { columna: entrada.columna ?? null, tipo_agregacion: entrada.tipo_agregacion || 'suma' }
}

/**
 * Solo aplica a Tablas: a diferencia del resto de posiciones (una cantidad fija de columnas de
 * valor por `calculo`), una tabla puede tener cualquier cantidad — se pueden agregar, quitar y
 * reordenar sin límite fijo (`services/generic_charts.py::generar_datos_tabla` ya acepta una
 * lista de cualquier tamaño). Siempre queda al menos una fila de selector: una tabla sin ninguna
 * columna de valor no tiene nada que calcular y cae al dato ficticio. Cada columna, además de qué
 * columna del archivo la alimenta, elige su propio tipo de agregación (sección 23:
 * suma/promedio/cantidad de valores únicos) — no es un ajuste único para toda la tabla, ya que
 * cada columna puede necesitar un cálculo distinto (p. ej. "Ventas" en suma y "Cliente" en
 * cantidad de valores únicos, en la misma tabla).
 */
function ColumnasTabla({ contexto, columnasElegidas, opciones, onCambiarColumna, onCambiarAgregacion, onAgregar, onQuitar, onMover }) {
  const lista = (columnasElegidas.length > 0 ? columnasElegidas : [null]).map(normalizarColumnaValorTabla)
  return (
    <div className="mb-2">
      <Form.Label className="mb-1" style={{ fontSize: '0.8rem' }}>Columnas</Form.Label>
      {lista.map((fila, i) => (
        <div key={i} className="mb-2 p-2 border rounded">
          <SelectorColumna
            etiqueta={`Columna ${i + 1}`} contexto={contexto} valor={fila.columna} opciones={opciones}
            onCambiar={onCambiarColumna(i)}
          />
          <SelectorTipoAgregacion
            contexto={`columna ${i + 1} de ${contexto}`} valor={fila.tipo_agregacion} onCambiar={onCambiarAgregacion(i)}
          />
          <div className="d-flex gap-1">
            <Button
              size="sm" variant="outline-secondary" onClick={() => onMover(i, 'arriba')} disabled={i === 0}
              aria-label={`Mover columna ${i + 1} de ${contexto} arriba`} title="Mover arriba"
            >
              ↑
            </Button>
            <Button
              size="sm" variant="outline-secondary" onClick={() => onMover(i, 'abajo')} disabled={i === lista.length - 1}
              aria-label={`Mover columna ${i + 1} de ${contexto} abajo`} title="Mover abajo"
            >
              ↓
            </Button>
            <Button
              size="sm" variant="outline-danger" onClick={() => onQuitar(i)} disabled={lista.length <= 1}
              aria-label={`Quitar columna ${i + 1} de ${contexto}`} title="Quitar columna"
            >
              ×
            </Button>
          </div>
        </div>
      ))}
      <Button size="sm" variant="outline-secondary" onClick={onAgregar}>+ Agregar columna</Button>
    </div>
  )
}

/** Selectores de columna(s)/tipo de cálculo/tipo de gráfico para una posición, según su
 * `calculo` — sin el filtro (`FiltroSlot`, siempre se agrega aparte, al final). `cambiar(campo)`
 * y `cambiarEnLista(campo, indice)` ya saben cómo empaquetar cada cambio (mismo contrato que
 * `onActualizarSlot(slotId, cambios)` del builder/mapeo); `cambiarLista(campo)` reemplaza la
 * lista completa de una sola vez (agregar/quitar/reordenar, solo lo usan las Tablas). */
export function camposParaSlot({ slot, propuesta, columnas, cambiar, cambiarEnLista, cambiarLista }) {
  const contexto = slot.titulo

  if (slot.calculo === 'kpi') {
    return (
      <>
        <SelectorTipoAgregacion contexto={contexto} valor={propuesta.tipo_agregacion} onCambiar={cambiar('tipo_agregacion')} permitirValorCelda={false} />
        <SelectorColumna etiqueta="Columna" contexto={contexto} valor={propuesta.columna_valor} opciones={columnas} onCambiar={cambiar('columna_valor')} />
      </>
    )
  }
  if (slot.calculo === 'chart') {
    return (
      <>
        <SelectorTipoGrafico contexto={contexto} calculo={slot.calculo} valor={propuesta.chart_type} valorDefecto={slot.tipoVisualizacion} onCambiar={cambiar('chart_type')} />
        <SelectorColumna etiqueta="Categoría" contexto={contexto} valor={propuesta.columna_categoria} opciones={columnas} onCambiar={cambiar('columna_categoria')} />
        <SelectorColumna etiqueta="Valor" contexto={contexto} valor={propuesta.columna_valor} opciones={columnas} onCambiar={cambiar('columna_valor')} />
      </>
    )
  }
  if (slot.calculo === 'multivalor') {
    return (
      <>
        <SelectorTipoGrafico contexto={contexto} calculo={slot.calculo} valor={propuesta.chart_type} valorDefecto={slot.tipoVisualizacion} onCambiar={cambiar('chart_type')} />
        <SelectorColumna etiqueta="Categoría" contexto={contexto} valor={propuesta.columna_categoria} opciones={columnas} onCambiar={cambiar('columna_categoria')} />
        {[0, 1].map((i) => (
          <SelectorColumna
            key={i} etiqueta={`Métrica ${i + 1}`} contexto={contexto} valor={propuesta.columnas_valor?.[i]} opciones={columnas}
            onCambiar={cambiarEnLista('columnas_valor', i)}
          />
        ))}
      </>
    )
  }
  if (slot.calculo === 'multiserie') {
    return (
      <>
        <SelectorTipoGrafico contexto={contexto} calculo={slot.calculo} valor={propuesta.chart_type} valorDefecto={slot.tipoVisualizacion} onCambiar={cambiar('chart_type')} />
        <SelectorColumna etiqueta="Categoría" contexto={contexto} valor={propuesta.columna_categoria} opciones={columnas} onCambiar={cambiar('columna_categoria')} />
        <SelectorColumna etiqueta="Serie" contexto={contexto} valor={propuesta.columna_serie} opciones={columnas} onCambiar={cambiar('columna_serie')} />
        <SelectorColumna etiqueta="Valor" contexto={contexto} valor={propuesta.columna_valor} opciones={columnas} onCambiar={cambiar('columna_valor')} />
      </>
    )
  }
  if (slot.calculo === 'dispersion') {
    return (
      <>
        <SelectorColumna etiqueta="Eje X" contexto={contexto} valor={propuesta.columna_valor} opciones={columnas} onCambiar={cambiar('columna_valor')} />
        <SelectorColumna etiqueta="Eje Y" contexto={contexto} valor={propuesta.columna_valor_y} opciones={columnas} onCambiar={cambiar('columna_valor_y')} />
      </>
    )
  }
  if (slot.calculo === 'tabla') {
    const listaColumnas = (propuesta.columnas_valor || []).map(normalizarColumnaValorTabla)
    const setLista = cambiarLista('columnas_valor')
    const base = () => (listaColumnas.length > 0 ? listaColumnas : [normalizarColumnaValorTabla(null)])
    return (
      <>
        <SelectorColumna etiqueta="Identidad de fila" contexto={contexto} valor={propuesta.columna_id} opciones={columnas} onCambiar={cambiar('columna_id')} />
        <ColumnasTabla
          contexto={contexto}
          columnasElegidas={listaColumnas}
          opciones={columnas}
          onCambiarColumna={(i) => (valor) => {
            const nueva = [...base()]
            nueva[i] = { ...nueva[i], columna: valor }
            setLista(nueva)
          }}
          onCambiarAgregacion={(i) => (valor) => {
            const nueva = [...base()]
            nueva[i] = { ...nueva[i], tipo_agregacion: valor }
            setLista(nueva)
          }}
          onAgregar={() => setLista([...base(), normalizarColumnaValorTabla(null)])}
          onQuitar={(i) => setLista(base().filter((_, idx) => idx !== i))}
          onMover={(i, direccion) => {
            const b = base()
            const destino = direccion === 'arriba' ? i - 1 : i + 1
            if (destino < 0 || destino >= b.length) return
            const nueva = [...b]
            ;[nueva[i], nueva[destino]] = [nueva[destino], nueva[i]]
            setLista(nueva)
          }}
        />
      </>
    )
  }
  return null
}
