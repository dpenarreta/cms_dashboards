# Editor visual de dashboards — reglas compartidas

Aplica en conjunto a `backend/cartera/services/dashboard_layout.py` (persistencia/validación) y
`frontend/src/components/dashboard-editor/` + `dashboard-generic/` (UI). Cambiar un lado sin el
otro rompe el contrato.

## Grid sin coordenadas

- `EditableGrid` usa un único contenedor `flex-wrap`: cada componente reserva `ancho/12` y el
  propio `flex-wrap` reordena todo solo. No existen coordenadas fila/columna que mantener a mano
  — no intentes calcular posiciones absolutas ni detectar superposición, es estructuralmente
  imposible con este layout.
- `order` es una secuencia global única (no se reinicia por fila). `row` se recalcula solo para
  auditoría/compatibilidad de esquema — no gobierna el renderizado, no lo uses para decidir layout.
- Ancho: selector discreto 2/3/4/6/8/9/12 (doceavos). Alto: presets o valor libre en px, mínimo
  60px. No agregues arrastre libre de bordes en píxeles (decisión de accesibilidad, ver README).

## Zonas y componentes personalizados

- Un componente con `config.zona === 'personal'` pertenece a la "Zona Personal": una zona dinámica
  siempre al final, visible solo si tiene 1+ componentes. No agregues componentes de datos/paleta
  a las zonas fijas de la plantilla — la paleta (`ComponentPaletteSidebar`) usa un `DndContext`
  separado del de `EditableGrid` con un único `droppable` (`zona-personal-drop`), así que soltar
  fuera de la Zona Personal es imposible por construcción, no por validación en tiempo de
  ejecución. No fusiones ambos `DndContext`.
- `DashboardComponent.Tipo` incluye `title`/`text` (separador/título presentacionales, sin datos)
  además de `kpi`/`chart`/`table`/`filter`/`filters_panel`/`message`/`alert`. Los presentacionales
  se crean con `agregar_componente_presentacional` (sin archivo/dataframe); los demás con
  `agregar_componente_generado`. No mezcles ambos caminos.

## Persistencia y versionado

- "Guardar cambios" envía el layout completo como una única operación atómica — no hay endpoint
  por componente para guardado batch. El backend compara la versión enviada contra la actual: si
  no coincide, responde `409` (alguien más guardó primero); el frontend debe ofrecer recargar, no
  sobrescribir en silencio.
- Cambios de Zona Personal (agregar componente vía paleta) se persisten **de inmediato** (POST +
  recarga), fuera del flujo borrador/"Guardar cambios" — no los mezcles con `layout.borrador`.
- Recalcular los datos NO reinicia el diseño: `plantilla.aplicar_mapeo` reconstruye las 13
  posiciones sobre `plantilla.slots_vigentes(dashboard_id)`, así que tamaño, orden, visibilidad,
  colores, título y configuración sobreviven a un archivo nuevo, a una reconfiguración y a la
  actualización automática. La única forma de volver al diseño de fábrica es pedirlo
  explícitamente.
- "Restablecer diseño" vuelve al diseño por defecto definido en código
  (`dashboard_layout.py`, no en datos de migración), afecta a **todos** los usuarios y no se puede
  deshacer — pide confirmación explícita (modal, nunca `window.confirm`).

## Agregar un cálculo nuevo

Un `calculo` (`mapeo['calculo']`) es de primera clase solo si está en los CUATRO lugares; si falta
alguno, el componente se ve pero no se puede reconfigurar desde la pantalla:

1. `generic_charts.py` — la función que lo computa.
2. `plantilla.py::_calcular_contenido_slot` — la rama que arma su `content` a partir del mapeo.
3. `dashboard_layout.py::_validar_mapeo_calculo` — la validación de sus parámetros propios (y, si
   se crea desde la Zona Personal, el bloque que arma el `mapeo` en `agregar_componente_generado`).
4. `SlotFields.jsx::CamposParaSlot` — el formulario con sus selectores.

`antiguedad_por_deudor` (antigüedad de los mayores deudores) se agregó así y sirve de referencia.

## Filtro de una posición

Dos formas, según `mapeo['tipo_filtro']` (ver `plantilla.py::_aplicar_filtro_slot`):

- **Por valores** (default): `columna_filtro` + `valores_filtro` (lista) + `operador_valor`
  (`'en'` incluye / `'no_en'` excluye). Sirve para cualquier posición, no solo KPI. `'no_en'` es lo
  que permite pedir "todo el saldo MENOS el anticipado" sin enumerar los demás valores —que además
  cambiarían si el archivo trae una categoría nueva—. Sin valores elegidos NO se filtra, cualquiera
  sea el operador: "ninguno de nada" excluiría el archivo entero.
- **Por días desde una fecha** (`'dias_vencidos'`, solo KPI): `columna_filtro` + `operador_filtro`
  + `dias_filtro`.

IMPORTANT: `valor_filtro` (un único valor) es la forma ANTERIOR y sigue siendo válida — hay mapeos
guardados con ella y no hay migración que los reescriba. Al leer, usá `plantilla.valores_filtro_de`,
que resuelve las dos; al escribir desde la interfaz, guardá `valores_filtro` y limpiá `valor_filtro`
para no dejar dos fuentes de lo mismo.

## Paginación de tablas

- Únicos tamaños permitidos: 5, 10, 25, 50, 100. Un `page_size` fuera de ese conjunto cae a 10 sin
  error, tanto en frontend (`Pagination.jsx`) como en backend
  (`dashboard_layout.validar_componentes`) — no aceptes valores arbitrarios en ningún lado.
  Exportar (`ExportarView`) ignora el `page_size` de pantalla: siempre exporta el total filtrado.

## Colores y gráficos

- Los colores de componente (principal/vencido/no vencido/sin gestión/texto/fondo) se validan como
  hex `#RGB`/`#RRGGBB` o `rgba(...)` **en ambos lados** (frontend y backend) — no confíes solo en
  la validación de un lado.
- `chart_type` está modelado pero la UI no permite cambiarlo (fuera de alcance documentado, no un
  olvido) — no implementes un selector de tipo de gráfico sin confirmarlo primero.
- Los colores de serie usan variables CSS (`var(--series-1)`, etc.), no hex fijos — Recharts las
  resuelve nativamente. Al agregar un gráfico nuevo, sigue ese patrón para que el modo oscuro
  (`:root[data-theme='dark']` en `dashboard.css`) lo re-temee sin cambios adicionales.
