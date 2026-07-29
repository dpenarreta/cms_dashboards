# Matriz de trazabilidad — Drill-down del dashboard de cartera

Fuente: `tests/qa/features/dashboard-portfolio-drilldown.feature`.

Convención de la columna **Estado**: `Aprobado` solo si la prueba indicada se ejecutó y pasó en
esta sesión (ver `tests/qa/test-execution-report.md` para el comando y la fecha exactos).
`Pendiente` = no se ejecutó ninguna prueba automatizada para ese criterio (verificación manual
únicamente, o no aplica). Ningún criterio se marca `Aprobado` sin una ejecución real registrada.

| ID | Criterio | Escenario | Prueba(s) que lo cubren | Automatizado | Estado |
|---|---|---|---|---|---|
| AC-CAR-001 | Sustituir Pareto por pastel | Mostrar cartera vencida por ciudad | `CarteraVencidaPorCiudadChart.test.jsx` | Sí | Aprobado |
| AC-CAR-002 | Mostrar leyenda de ciudades | Mostrar leyenda | `CarteraVencidaPorCiudadChart.test.jsx` | Sí | Aprobado |
| AC-CAR-003 | Tooltip con monto y % | Mostrar monto y porcentaje | — | No (Recharts no expone el hover de forma fiable en jsdom) | Verificado manualmente en navegador |
| AC-CAR-004 | Abrir detalle por ciudad | Abrir detalle de Quito | `CarteraVencidaPorCiudadChart.test.jsx`, backend `test_filtro_por_ciudad`, `test_coherencia_entre_grafico_de_ciudad_y_detalle` | Sí | Aprobado |
| AC-CAR-005 | Abrir registros gestionados | Consultar Gestionado | `CausalesChart.test.jsx` | Sí | Aprobado |
| AC-CAR-006 | Filtrar desde otro gráfico (patrón general) | Seleccionar columna | `KpiRow.test.jsx`, `RecuperadorCausalMatrix.test.jsx`, `CausalesChart.test.jsx` (mismo contrato `useDrilldown`) | Sí | Aprobado |
| AC-CAR-007 | Conservar contexto al volver | Conservar filtros globales | `PortfolioDetailPanel.test.jsx` | Sí | Aprobado |
| AC-CAR-008 | Coherencia gráfico/detalle | Coincidencia de montos | backend `test_coherencia_entre_grafico_de_ciudad_y_detalle` | Sí | Aprobado |
| AC-CAR-009 | Rechazo sin permisos | Acceso denegado | — | No aplica | **No aplica** — el proyecto no implementa autenticación/autorización (decisión documentada en `README.md`, sección "Limitaciones conocidas"). Implementarlo requiere una funcionalidad de login fuera de este alcance. |
| AC-CAR-010 | Vista sin resultados | Estado sin resultados | `DetalleTable.test.jsx` | Sí | Aprobado |
| AC-CAR-011 | Paginación desde backend | Paginar detalle | backend `test_endpoints_get_tras_procesar` | Sí (backend) / manual (clics de paginación en UI) | Aprobado (backend) |
| AC-CAR-012 | Agrupación "Otras ciudades" | Abrir agrupación | `CarteraVencidaPorCiudadChart.test.jsx`, backend `test_agrupa_otras_ciudades_cuando_hay_mas_de_8`, `test_filtro_multivalor_causal_otras` | Sí | Aprobado |
| AC-CAR-013 | Navegación por teclado | Navegar con teclado | `KpiRow.test.jsx`, `RecuperadorCausalMatrix.test.jsx` | Sí (para las afordancias en HTML plano: tarjetas KPI y celdas de matriz) | Aprobado (parcial — ver limitación abajo) |
| AC-CAR-014 | Drill-down por recuperador | Seleccionar barra de recuperador | `RecuperadoresChart.test.jsx` (render), clic en barra SVG no automatizado | Parcial | Verificado manualmente en navegador |
| AC-CAR-015 | Drill-down causal-por-recuperador | Seleccionar segmento apilado | — | No (marca SVG de Recharts) | Verificado manualmente en navegador |
| AC-CAR-016 | Drill-down por celda de matriz | Seleccionar celda | `RecuperadorCausalMatrix.test.jsx` | Sí | Aprobado |
| AC-CAR-017 | Drill-down por KPI >120 días | Seleccionar tarjeta KPI | `KpiRow.test.jsx` | Sí | Aprobado |
| AC-CAR-018 | Quitar filtro de drill-down sin perder los globales | Quitar filtro de ciudad | `PortfolioDetailPanel.test.jsx` | Sí | Aprobado |

## Limitación conocida sobre AC-CAR-013 (teclado)

Los **marcadores SVG individuales** de Recharts (sectores de pastel, barras, segmentos apilados)
no son elementos DOM enfocables de forma nativa y esta librería no expone una API para asignarles
`tabIndex`/`role` por marca. Por eso, el foco de teclado se implementó en las **afordancias HTML
paralelas** que sí acompañan a cada gráfico interactivo: la leyenda-lista de
`CarteraVencidaPorCiudadChart` y `CausalesChart` (elementos `<button>`), las tarjetas KPI
(`role="button"` + `tabIndex`) y las celdas de `RecuperadorCausalMatrix` (`role="button"` +
`tabIndex`). `RecuperadoresChart`, `TopClientesChart` y `RecuperadorCausalChart` no tienen hoy una
afordancia de teclado equivalente a su interacción por mouse — accionar su drill-down por
teclado queda pendiente como mejora futura (ver `docs/dashboard.md`).
