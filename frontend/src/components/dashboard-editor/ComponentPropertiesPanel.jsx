import { useEffect, useState } from 'react'
import { Alert, Button, Form, Offcanvas } from 'react-bootstrap'
import WidthHeightControls from './WidthHeightControls'
import FilterFieldReorderList from './FilterFieldReorderList'
import { POSICIONES_LEYENDA } from '../../utils/legendPosition'

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/
const PAGE_SIZES_FIJOS = [5, 10, 25, 50, 100]
// Espejo de `TIPOS_CON_LEYENDA` en `cartera/services/dashboard_layout.py`: los únicos tipos de
// gráfica que dibujan una leyenda, y por lo tanto los únicos donde tiene sentido reposicionarla.
const TIPOS_CON_LEYENDA = new Set(['barras_agrupadas', 'barras_apiladas', 'area_apilada', 'pastel', 'dona'])
// Tipos de gráfica de varias series (barras agrupadas/apiladas, área apilada): reparten un color
// por serie (`content.series`), no por categoría.
const TIPOS_MULTISERIE = new Set(['barras_agrupadas', 'barras_apiladas', 'area_apilada'])

// Colores realmente pintados hoy cuando no hay override (`styles/dashboard.css`, variables
// `--series-1`.."--series-8"/`--text-primary`/`--surface-1`) — a diferencia de los colores
// institucionales (`--color-primary`, etc.), ThemeProvider nunca reescribe estas variables en
// runtime, así que su valor estático es siempre el color efectivamente en pantalla. Se usan para
// precargar cada selector con el color "actual" en vez de dejarlo en blanco cuando todavía no hay
// un override guardado. Mismo orden que `PALETA_CATEGORICA` (utils/colors.js), que es la que
// reparte estos colores por índice en los componentes Generic*.
const PALETA_HEX = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
const COLOR_TEXTO_HEX = '#000000'
const COLOR_FONDO_HEX = '#ffffff'

/** Construye las filas de color a mostrar para un componente: cada una es `{id, etiqueta, valor,
 * porDefecto, onCambiar(valor)}` — `onCambiar` ya sabe cómo empaquetar ese cambio dentro de
 * `styles` (colector plano para KPI/título/fondo, mapa por nombre para categorías/series), así el
 * panel solo necesita renderizar la lista sin saber de la forma interna de cada campo.
 *
 * "Cada categoría/serie debe tener su propio color editable" (no un único "color principal"
 * compartido): una tarjeta KPI solo tiene un acento opcional; una tabla no tiene barras/porciones
 * que teñir (solo título y fondo); una línea es un único trazo continuo (un color, no uno por
 * punto); el resto (barras, pastel/dona, agrupadas/apiladas) reparten un color por cada categoría
 * o serie que traiga el propio componente (`content.categorias`/`content.series`). */
function filasColorPara(componente) {
  const estilos = componente.styles || {}
  const filaTextoYFondo = [
    { id: 'colorTexto', etiqueta: 'Color del título', porDefecto: COLOR_TEXTO_HEX, valor: estilos.colorTexto, onCambiar: (v) => ({ colorTexto: v }) },
    { id: 'colorFondo', etiqueta: 'Color de fondo', porDefecto: COLOR_FONDO_HEX, valor: estilos.colorFondo, onCambiar: (v) => ({ colorFondo: v }) },
  ]

  if (componente.type === 'kpi') {
    return [{ id: 'colorPrincipal', etiqueta: 'Color principal', porDefecto: '', valor: estilos.colorPrincipal, onCambiar: (v) => ({ colorPrincipal: v }) }]
  }
  if (componente.chart_type === 'tabla') {
    return filaTextoYFondo
  }
  if (componente.chart_type === 'lineas' || componente.chart_type === 'dispersion') {
    const etiqueta = componente.chart_type === 'dispersion' ? 'Color de los puntos' : 'Color de la línea'
    return [
      { id: 'colorPrincipal', etiqueta, porDefecto: PALETA_HEX[0], valor: estilos.colorPrincipal, onCambiar: (v) => ({ colorPrincipal: v }) },
      ...filaTextoYFondo,
    ]
  }
  if (TIPOS_MULTISERIE.has(componente.chart_type)) {
    const series = componente.content?.series || []
    const coloresPorSerie = estilos.coloresPorSerie || {}
    const filasSerie = series.map((s, i) => ({
      id: `serie-${s.nombre}`, etiqueta: `Color de "${s.nombre}"`, porDefecto: PALETA_HEX[i % PALETA_HEX.length],
      valor: coloresPorSerie[s.nombre], onCambiar: (v) => ({ coloresPorSerie: { ...coloresPorSerie, [s.nombre]: v } }),
    }))
    return [...filasSerie, ...filaTextoYFondo]
  }
  if (componente.type === 'chart') {
    const categorias = componente.content?.categorias || []
    const coloresPorCategoria = estilos.coloresPorCategoria || {}
    const filasCategoria = categorias.map((cat, i) => ({
      id: `categoria-${cat}`, etiqueta: `Color de "${cat}"`, porDefecto: PALETA_HEX[i % PALETA_HEX.length],
      valor: coloresPorCategoria[cat], onCambiar: (v) => ({ coloresPorCategoria: { ...coloresPorCategoria, [cat]: v } }),
    }))
    return [...filasCategoria, ...filaTextoYFondo]
  }
  return []
}

/** Qué escribir en `styles` cuando se pulsa "Restablecer colores": limpia el/los campo(s) de
 * datos (el mapa completo por categoría/serie, no solo la última fila tocada) más título/fondo. */
function estilosDeRestablecerPara(componente) {
  if (componente.type === 'kpi') return { colorPrincipal: '' }
  if (componente.chart_type === 'tabla') return { colorTexto: '', colorFondo: '' }
  if (componente.chart_type === 'lineas' || componente.chart_type === 'dispersion') {
    return { colorPrincipal: '', colorTexto: '', colorFondo: '' }
  }
  if (TIPOS_MULTISERIE.has(componente.chart_type)) {
    return { coloresPorSerie: {}, colorTexto: '', colorFondo: '' }
  }
  if (componente.type === 'chart') return { coloresPorCategoria: {}, colorTexto: '', colorFondo: '' }
  return {}
}

function CampoColor({ etiqueta, valor, porDefecto, onCambiar }) {
  const [texto, setTexto] = useState(valor || porDefecto || '')
  const [errorLocal, setErrorLocal] = useState('')

  useEffect(() => setTexto(valor || porDefecto || ''), [valor, porDefecto])

  const aplicar = (nuevo) => {
    setTexto(nuevo)
    if (nuevo === '') {
      setErrorLocal('')
      onCambiar('')
      return
    }
    if (!HEX_RE.test(nuevo)) {
      setErrorLocal('Color inválido. Use formato hexadecimal, ej. #1F4E78.')
      return
    }
    setErrorLocal('')
    onCambiar(nuevo)
  }

  return (
    <Form.Group className="mb-2">
      <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>{etiqueta}</Form.Label>
      <div className="d-flex gap-2 align-items-center">
        <Form.Control
          type="color"
          style={{ width: 44, padding: 2 }}
          value={HEX_RE.test(texto) ? texto : '#ffffff'}
          onChange={(e) => aplicar(e.target.value)}
          aria-label={`${etiqueta} (selector visual)`}
        />
        <Form.Control
          size="sm"
          value={texto}
          placeholder="#RRGGBB"
          onChange={(e) => aplicar(e.target.value)}
          aria-label={`${etiqueta} (hexadecimal)`}
        />
      </div>
      {errorLocal && <div className="text-danger" style={{ fontSize: '0.75rem' }}>{errorLocal}</div>}
    </Form.Group>
  )
}

export default function ComponentPropertiesPanel({
  componente, onCerrar, onActualizarContenido, onActualizarEstilos, onCambiarAncho, onCambiarAlto, onActualizarConfig,
}) {
  if (!componente) return null

  const filasColor = filasColorPara(componente)
  const restablecerColores = () => onActualizarEstilos(componente.component_id, estilosDeRestablecerPara(componente))

  return (
    <Offcanvas show={Boolean(componente)} onHide={onCerrar} placement="end" style={{ width: 380 }}>
      <Offcanvas.Header closeButton>
        <Offcanvas.Title>Configurar componente</Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <Alert variant="secondary" className="py-2" style={{ fontSize: '0.8rem' }}>
          {componente.component_id}
        </Alert>

        <h6>Información general</h6>
        <Form.Group className="mb-2" controlId={`titulo-${componente.component_id}`}>
          <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>Título</Form.Label>
          <Form.Control
            size="sm"
            value={componente.content?.titulo || ''}
            onChange={(e) => onActualizarContenido(componente.component_id, { titulo: e.target.value })}
            maxLength={200}
          />
        </Form.Group>
        <Form.Group className="mb-3" controlId={`descripcion-${componente.component_id}`}>
          <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>Descripción</Form.Label>
          <Form.Control
            as="textarea"
            rows={2}
            size="sm"
            value={componente.content?.descripcion || ''}
            onChange={(e) => onActualizarContenido(componente.component_id, { descripcion: e.target.value })}
            maxLength={500}
          />
        </Form.Group>

        <h6>Tamaño</h6>
        <div className="mb-3">
          <WidthHeightControls
            width={componente.width}
            height={componente.height}
            onCambiarAncho={(w) => onCambiarAncho(componente.component_id, w)}
            onCambiarAlto={(h) => onCambiarAlto(componente.component_id, h)}
          />
        </div>

        {filasColor.length > 0 && (
          <>
            <div className="d-flex justify-content-between align-items-center mb-2">
              <h6 className="mb-0">Colores</h6>
              <Button size="sm" variant="link" onClick={restablecerColores}>Restablecer colores</Button>
            </div>
            {filasColor.map((f) => (
              <CampoColor
                key={f.id}
                etiqueta={f.etiqueta}
                valor={f.valor}
                porDefecto={f.porDefecto}
                onCambiar={(valor) => onActualizarEstilos(componente.component_id, f.onCambiar(valor))}
              />
            ))}
          </>
        )}

        {TIPOS_CON_LEYENDA.has(componente.chart_type) && (
          <>
            <h6>Leyenda</h6>
            <Form.Group className="mb-3" controlId={`leyenda-posicion-${componente.component_id}`}>
              <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>Posición de la leyenda</Form.Label>
              <Form.Select
                size="sm"
                value={componente.config?.leyenda_posicion || 'abajo'}
                onChange={(e) => onActualizarConfig(componente.component_id, {
                  ...componente.config,
                  leyenda_posicion: e.target.value,
                })}
              >
                {POSICIONES_LEYENDA.map((p) => (
                  <option key={p.id} value={p.id}>{p.etiqueta}</option>
                ))}
              </Form.Select>
            </Form.Group>
          </>
        )}

        {componente.type === 'table' && (
          <>
            <h6>Paginación</h6>
            <Form.Group className="mb-3" controlId={`page-size-${componente.component_id}`}>
              <Form.Label className="mb-1" style={{ fontSize: '0.85rem' }}>Registros visibles por defecto</Form.Label>
              <Form.Select
                size="sm"
                value={componente.config?.defaultPageSize || 10}
                onChange={(e) => onActualizarConfig(componente.component_id, {
                  ...componente.config,
                  defaultPageSize: Number(e.target.value),
                })}
              >
                {(componente.config?.allowedPageSizes || PAGE_SIZES_FIJOS).map((n) => (
                  <option key={n} value={n}>{n} registros</option>
                ))}
              </Form.Select>
            </Form.Group>
          </>
        )}

        {componente.type === 'filters_panel' && componente.config?.filtros && (
          <>
            <h6>Orden de los filtros</h6>
            <FilterFieldReorderList
              filtros={componente.config.filtros}
              onCambiar={(nuevosFiltros) => onActualizarConfig(componente.component_id, { ...componente.config, filtros: nuevosFiltros })}
            />
          </>
        )}

        <Button variant="outline-secondary" size="sm" className="mt-2" onClick={onCerrar}>Cerrar</Button>
      </Offcanvas.Body>
    </Offcanvas>
  )
}
