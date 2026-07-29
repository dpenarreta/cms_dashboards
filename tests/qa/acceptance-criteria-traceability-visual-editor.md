# Matriz de trazabilidad — Editor visual del dashboard

Fuente: `tests/qa/features/dashboard-visual-editor.feature`.

Misma convención que `acceptance-criteria-traceability.md`: `Aprobado` solo si la prueba indicada
se ejecutó y pasó en esta sesión (ver `tests/qa/test-execution-report.md`). `Pendiente` = sin
prueba automatizada (verificación manual únicamente, o no aplica).

| ID | Criterio | Escenario | Prueba(s) que lo cubren | Automatizado | Estado |
|---|---|---|---|---|---|
| AC-EDT-001 | Activar modo edición | Activar modo edición | `EditModeToolbar.test.jsx` | Sí | Aprobado |
| AC-EDT-002 | Sin permiso de editar no ve el botón | Usuario sin permiso de edición | `EditModeToolbar.test.jsx` (permisos) | Sí | Aprobado |
| AC-EDT-003 | Sin permiso de ver, ningún control | Usuario sin permiso de ver | `EditModeToolbar.test.jsx` (permisos) | Sí | Aprobado |
| AC-EDT-004 | Reordenar por arrastre | Reordenar arrastrando | `useDashboardLayout.test.js` (`reordenarPorIds`, lógica subyacente) | Parcial (la lógica de reordenamiento sí; el evento de puntero de dnd-kit no) | Verificado manualmente en navegador (arrastre real con mouse) |
| AC-EDT-005 | Reordenar con botones de mover | Mover abajo | `useDashboardLayout.test.js` (`moverComponente`), `ComponentWrapper.test.jsx`, `MoveButtons.test.jsx` | Sí | Aprobado |
| AC-EDT-006 | Mover al inicio/al final | Mover al inicio/al final | `useDashboardLayout.test.js`, `MoveButtons.test.jsx` | Sí | Aprobado |
| AC-EDT-007 | Cambiar ancho por selector discreto | Cambiar ancho | `ComponentPropertiesPanel.test.jsx`, backend `test_rechaza_ancho_fuera_de_rango` | Sí | Aprobado |
| AC-EDT-008 | Cambiar alto por preset | Cambiar alto | `WidthHeightControls.test.jsx` | Sí | Aprobado |
| AC-EDT-009 | Editar título | Editar título | `ComponentPropertiesPanel.test.jsx` | Sí | Aprobado |
| AC-EDT-010 | Color válido se aplica | Color principal válido | `ComponentPropertiesPanel.test.jsx`, backend `test_acepta_color_hex_y_rgba` | Sí | Aprobado |
| AC-EDT-011 | Color inválido se rechaza | Rechazar color inválido | `ComponentPropertiesPanel.test.jsx` (frontend), backend `test_rechaza_color_invalido` | Sí | Aprobado |
| AC-EDT-012 | Sanitizar `<script>` en el título | Sanitizar contenido inseguro | backend `test_sanitiza_etiquetas_html_del_titulo` | Sí | Aprobado |
| AC-EDT-013 | No corromper texto legítimo con ">" | No corromper "Cartera > 120 días" | backend `test_titulo_con_signo_mayor_que_no_se_corrompe` (regresión) | Sí | Aprobado |
| AC-EDT-014 | Ocultar componente | Ocultar componente | `ComponentWrapper.test.jsx`, backend `test_ocultar_componente_registra_auditoria` | Sí | Aprobado |
| AC-EDT-015 | Mostrar componente oculto | Mostrar componente oculto | `ComponentWrapper.test.jsx` | Sí | Aprobado |
| AC-EDT-016 | Guardar persiste la configuración | Guardar cambios | `useDashboardLayout.test.js` (`guardar`), backend `test_guarda_cambio_de_orden_tamano_color_y_texto` | Sí | Aprobado |
| AC-EDT-017 | Cancelar con cambios pide confirmación | Cancelar con cambios sin guardar | `EditModeToolbar.test.jsx` | Sí | Aprobado |
| AC-EDT-018 | Cancelar sin cambios no pide confirmación | Cancelar sin cambios pendientes | `EditModeToolbar.test.jsx` | Sí | Aprobado |
| AC-EDT-019 | Restablecer pide confirmación | Restablecer diseño predeterminado | `EditModeToolbar.test.jsx`, backend `test_restablecer_recupera_visibilidad_y_registra_auditoria` | Sí | Aprobado |
| AC-EDT-020 | Conflicto de versión al guardar | Conflicto de versión concurrente | `useDashboardLayout.test.js` (409), backend `test_conflicto_de_version_no_sobrescribe` | Sí | Aprobado |
| AC-EDT-021 | Auditoría de cambios | Auditoría de cambios | backend `test_guarda_cambio_de_orden_tamano_color_y_texto`, `test_versions_devuelve_historial_mas_reciente_primero` | Sí | Aprobado |
| AC-EDT-022 | Vista previa sin round-trip | Vista previa oculta el chrome | — | No (requiere observar ausencia de llamadas de red en un montaje completo de la página) | Verificado manualmente en navegador (sin peticiones adicionales al alternar Vista previa) |
| AC-EDT-023 | Cambiar estilo no repite consulta de datos | Cambiar estilo no refetch | `useDashboardLayout.test.js` (`actualizarEstilos`/`actualizarContenido` no llaman al servicio de layout) | Sí (a nivel del hook de layout) | Aprobado |
| AC-EDT-024 | Reordenar campos del panel de filtros | Reordenar campos de filtro | `FilterFieldReorderList.test.jsx` | Sí | Aprobado |
| AC-EDT-025 | Sin superposición ni scroll horizontal | Componentes no se superponen | — | No (layout visual real) | Verificado manualmente en navegador (flex-wrap por construcción; ver limitación abajo) |
| AC-EDT-026 | Funciona en pantalla angosta (móvil) | Dashboard editable en móvil | — | No | Pendiente — no se verificó en un viewport móvil real en esta sesión (ver limitación abajo) |
| AC-EDT-027 | Rechazar componente desconocido | Rechazar componente desconocido | backend `test_rechaza_componente_desconocido` | Sí | Aprobado |
| AC-EDT-028 | Sin permiso de restablecer, oculta esa opción | Usuario sin permiso de restablecer | `EditModeToolbar.test.jsx` (permisos) | Sí | Aprobado |

## Limitaciones conocidas

- **AC-EDT-004 (arrastre real con mouse)**: igual que con las marcas SVG de Recharts en el
  drill-down, `dnd-kit` no se simula con eventos de puntero sintéticos en jsdom de forma
  fiable. Se probó la función de reordenamiento subyacente (`reordenarPorIds`, que comparte el
  mismo `recalcularFilas` que `moverComponente`) y se verificó el arrastre real con mouse en el
  navegador durante el smoke test manual (sección correspondiente de
  `tests/qa/test-execution-report.md`).
- **AC-EDT-022 (vista previa sin round-trip)**: confirmar la ausencia de peticiones de red es
  más confiable observando la pestaña de red del navegador real que interceptando `fetch`/axios
  en un test aislado del toggle; se verificó manualmente.
- **AC-EDT-025 (no superposición/scroll horizontal)**: `EditableGrid` usa `flex-wrap` con anchos
  en fracciones de 12 columnas, lo que evita la superposición **por construcción** (no hay
  coordenadas x/y que puedan chocar). Verificado visualmente en el smoke test manual; no hay una
  prueba automatizada de layout/geometría en jsdom.
- **AC-EDT-026 (móvil)**: no se verificó en un viewport móvil real durante esta sesión. El CSS
  existente ya usa `Col md={4}` en paneles como `FiltersPanel` y clases responsivas de Bootstrap,
  pero el editor visual en sí (con sus controles de arrastre/engranaje) no se probó explícitamente
  en una pantalla angosta. Queda como verificación pendiente antes de considerar esta capacidad
  completamente cerrada.
