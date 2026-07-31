# Matriz de trazabilidad — Registros visibles en matrices y tablas

Fuente: `tests/qa/dashboard_matrices_pagination.feature`.

Misma convención que `acceptance-criteria-traceability.md`: `Aprobado` solo si la prueba indicada
se ejecutó y pasó en esta sesión. `Verificado por diseño` = el comportamiento se garantiza por la
forma en que está construido el código (dos rutas de datos separadas, un parámetro que nunca se
envía, etc.), sin que exista todavía una prueba automatizada dedicada a ese escenario puntual.
`Pendiente` = sin prueba automatizada ni verificación manual en esta sesión.

| ID | Criterio | Escenario | Prueba(s) que lo cubren | Automatizado | Estado |
|---|---|---|---|---|---|
| AC-PAG-001 | Default 10 registros | Mostrar diez registros de forma predeterminada | Backend `test_componentes_tabla_traen_configuracion_de_paginacion_por_defecto`; frontend `Pagination.test.jsx` (el selector refleja el `pageSize` recibido); `useDetalleCartera.js` (`PAGE_SIZE_DEFECTO = 10`) | Sí | Aprobado |
| AC-PAG-002 | Seleccionar 5 registros, vuelve a página 1 | Seleccionar cinco registros por página | `DetalleTable.test.jsx` ("cambiar el tamaño de página vuelve a consultar desde la página 1 con el nuevo tamaño"), `Pagination.test.jsx` (callback con el valor numérico elegido) | Sí | Aprobado |
| AC-PAG-003 | Las 5 cantidades permitidas (5/10/25/50/100) | Seleccionar una cantidad permitida | Backend `test_page_size_valido_se_respeta` (los 5 valores); `Pagination.jsx` renderiza `allowedPageSizes` completo | Sí | Aprobado |
| AC-PAG-004 | Mantener filtros al cambiar cantidad | Mantener filtros al cambiar la cantidad de registros | Verificado por diseño: `useDetalleCartera.cargar` arma `params` con `...filtros` en cada solicitud, incluida la que dispara el cambio de `pageSize`; no se limpia ningún filtro al cambiar `pageSize` | Parcial (arquitectura, sin test de integración dedicado) | Verificado por diseño |
| AC-PAG-005 | Mantener ordenamiento al cambiar cantidad | Mantener el ordenamiento | Verificado por diseño: `orden` es estado independiente de `pageSize` en `useDetalleCartera`, no se resetea al cambiar el tamaño de página | Parcial (arquitectura, sin test de integración dedicado) | Verificado por diseño |
| AC-PAG-006 | Configurar cantidad por defecto en modo edición | Configurar la cantidad predeterminada en modo edición | `ComponentPropertiesPanel.test.jsx` ("cambiar el selector de registros por defecto invoca onActualizarConfig"); backend `test_cambiar_solo_config_registra_auditoria_de_tipo_config`, `test_page_size_por_defecto_invalido_cae_al_fallback` | Sí | Aprobado |
| AC-PAG-007 | Preferencia temporal no altera la config general | No modificar la configuración general desde la visualización | Verificado por diseño: el selector en modo visualización solo llama a `cambiarPageSize`/`usePaginacionCliente` (estado local de React); únicamente `ComponentPropertiesPanel` (modo edición) invoca `onActualizarConfig`, que es el único camino que persiste en `DashboardComponent.config` | Parcial (arquitectura, sin test end-to-end de la sesión completa) | Verificado por diseño |
| AC-PAG-008 | `page_size` no permitido usa el valor por defecto | Validar un tamaño de página no permitido | Backend `test_page_size_no_permitido_usa_fallback_sin_error`, `test_page_size_no_numerico_usa_fallback_sin_error` (mismo código de validación `_resolver_page_size` que rechazaría también 500) | Sí | Aprobado |
| AC-PAG-009 | Resumen "Mostrando X a Y de Z registros" | Mostrar el resumen de resultados | `Pagination.test.jsx` ("muestra el resumen..."), con los mismos valores del escenario (página 2, 25 por página, 248 registros → "Mostrando 26 a 50 de 248 registros") | Sí | Aprobado |
| AC-PAG-010 | Exportar todo lo filtrado, no solo la página visible | Exportar todos los resultados filtrados | Verificado por diseño: `ExportarView`/`paramsExport` en `DetalleTable.jsx` nunca incluyen `page`/`page_size`, exportan siempre el dataset completo filtrado; cubierto además por el test backend existente `test_exportar_excel` | Parcial (sin test dedicado que compare recuento exportado vs. página visible) | Verificado por diseño |
| AC-PAG-011 | Paginación usable en móvil sin scroll horizontal | Adaptar la paginación en dispositivos móviles | CSS `.pagination-bar` + `@media (max-width: 576px)` en `dashboard.css` | No (requiere un viewport real) | Pendiente — no se verificó en un viewport móvil real en esta sesión |

## Limitaciones conocidas

- **AC-PAG-004/005/007/010 ("verificado por diseño")**: el comportamiento se deriva directamente
  de cómo están separados los estados y los parámetros (mismo patrón que el resto del código:
  `filtros`/`orden` viven en estado independiente de `pageSize`, y solo `ComponentPropertiesPanel`
  llama a `onActualizarConfig`). No se escribió una prueba de integración de extremo a extremo que
  monte el dashboard completo y simule la sesión descrita en el escenario; los tests unitarios
  existentes cubren cada pieza por separado.
- **AC-PAG-011 (móvil)**: igual que `AC-EDT-026` en el editor visual, jsdom no mide layout real
  (overflow horizontal, tamaño de toque), así que esto requiere una verificación manual en un
  navegador con un viewport de 375px, no realizada en esta sesión.
