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
- "Restablecer diseño" vuelve al diseño por defecto definido en código
  (`dashboard_layout.py`, no en datos de migración), afecta a **todos** los usuarios y no se puede
  deshacer — pide confirmación explícita (modal, nunca `window.confirm`).

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
