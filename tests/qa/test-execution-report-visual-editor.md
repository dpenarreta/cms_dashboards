# Reporte de ejecución de pruebas — Editor visual del dashboard

Fecha de ejecución: 2026-07-29. Entorno: SQL Server local (`cms_dashboards`), backend Django
(`http://localhost:8000`), frontend Vite (`http://localhost:5173`).

## Backend

Comando:

```bash
cd backend
python manage.py test cartera
```

Resultado:

```
Ran 68 tests in 1.806s
OK
```

Incluye, además de la suite previa (50 pruebas del drill-down), las pruebas nuevas del editor
visual (`cartera/tests/test_dashboard_layout.py`, 15 pruebas):

- `test_get_crea_layout_por_defecto`, `test_dashboard_no_reconocido_da_error`
- `test_guarda_cambio_de_orden_tamano_color_y_texto` (AC-EDT-016, 021)
- `test_ocultar_componente_registra_auditoria` (AC-EDT-014)
- `test_titulo_con_signo_mayor_que_no_se_corrompe` (regresión — AC-EDT-013)
- `test_sanitiza_etiquetas_html_del_titulo` (AC-EDT-012)
- `test_conflicto_de_version_no_sobrescribe` (AC-EDT-020)
- `test_rechaza_componente_desconocido`, `test_rechaza_ancho_fuera_de_rango`,
  `test_rechaza_color_invalido`, `test_acepta_color_hex_y_rgba` (AC-EDT-007, 010, 011, 027)
- `test_restablecer_recupera_visibilidad_y_registra_auditoria` (AC-EDT-019)
- `test_versions_devuelve_historial_mas_reciente_primero` (AC-EDT-021)
- `test_todos_los_permisos_concedidos_sin_autenticacion`,
  `test_endpoint_respeta_el_punto_unico_de_verificacion` (AC-EDT-002, 003, 028)

## Frontend

Comando:

```bash
cd frontend
npm run test
```

Resultado:

```
Test Files  18 passed (18)
Tests  94 passed (94)
```

Archivos de prueba nuevos de este cambio (58 pruebas nuevas sobre las 36 previas):

- `useDashboardLayout.test.js` — carga, `activarEdicion`, `moverComponente` (abajo/arriba/inicio/
  fin, incluida la regresión de `recalcularFilas` descrita abajo), `reordenarPorIds`,
  `actualizarEstilos`/`actualizarContenido` sin round-trip, `guardar` (incluido conflicto 409),
  `cancelar`, `restablecer`, `hayCambiosSinGuardar` (AC-EDT-004, 005, 006, 016, 017, 018, 020, 023)
- `EditModeToolbar.test.jsx` — activar edición, gating por permisos, confirmación de cancelar y
  restablecer, guardar con nombre de auditoría, deshabilitado mientras carga (AC-EDT-001, 002,
  003, 017, 018, 019, 028)
- `ComponentPropertiesPanel.test.jsx` — título, descripción, color válido/inválido, restablecer
  colores, ancho, reorden de filtros condicional (AC-EDT-007, 009, 010, 011)
- `WidthHeightControls.test.jsx` — presets de alto, alto personalizado con mínimo de 60px, ancho
  (AC-EDT-007, 008)
- `MoveButtons.test.jsx` — las cuatro direcciones y los estados deshabilitados (AC-EDT-005, 006)
- `ComponentWrapper.test.jsx` — visible/oculto, mostrar/ocultar, gating de `permiteEstilo`, botón
  de mover (AC-EDT-005, 014, 015)
- `FilterFieldReorderList.test.jsx` — mover campo, límites, visibilidad, etiqueta (AC-EDT-024)

### Regresión encontrada y corregida durante el smoke test manual

El smoke test manual (ver más abajo) encontró dos fallas reales que no habían aparecido en las
pruebas unitarias porque dependían del layout por defecto completo y de la interacción real con
`dnd-kit`:

1. **Dispersión de componentes**: el layout por defecto del backend asignaba `order` como único
   solo *dentro de cada fila* (1-6 repetido en cada `row`), pero `EditableGrid` ordena todos los
   componentes globalmente por `order` sin considerar `row`. Los 6 KPIs y otros componentes con
   `order` repetido entre filas terminaban dispersos por toda la página en vez de agrupados.
   Corregido en `backend/cartera/services/dashboard_layout.py`: `order` ahora es una secuencia
   global única (1..17) en el layout por defecto.
2. **"Mover abajo"/"Mover arriba" no reordenaban nada**: `recalcularFilas` (en
   `useDashboardLayout.js`) volvía a ordenar el array de entrada por el campo `order` **viejo**
   antes de reasignar valores nuevos, deshaciendo exactamente el reordenamiento manual que
   `moverComponente`/`reordenarPorIds` acababan de construir. Corregido eliminando ese reordenamiento
   interno — la función ahora confía en el orden del array que le pasan sus llamadores. Esto
   afectaba tanto a los botones de mover como al arrastre con `dnd-kit` (ambos pasan por
   `recalcularFilas`), y quedó cubierto con pruebas de regresión en `useDashboardLayout.test.js`.

Ambas correcciones se verificaron con las 94 pruebas de Vitest y con una repetición completa del
smoke test manual en el navegador tras el fix.

## Verificación manual (navegador)

Realizada con Chrome vía las herramientas de automatización, contra el backend/frontend reales y
el archivo sintético `backend/cartera/tests/fixtures/cartera_ejemplo.xlsx` (sin datos reales).
Cubrió específicamente lo que no es automatizable con Vitest/jsdom:

- Orden visual correcto de los 17 componentes tras el fix de `order` (AC-EDT-004 a 006, 025).
- Arrastre real con mouse de una tarjeta KPI a otra posición, usando `dnd-kit` (AC-EDT-004).
- Edición en vivo de título y color de un componente reflejada de inmediato (AC-EDT-009, 010).
- Ocultar/mostrar un componente en modo edición (AC-EDT-014, 015).
- Guardar cambios (orden, ocultar, título, color) y recargar la página completa (nueva subida del
  archivo) para confirmar que el layout persiste en SQL Server (AC-EDT-016).
- Cancelar con cambios sin guardar: aparece el modal de confirmación y, al confirmar, revierte al
  último guardado (AC-EDT-017).
- Restablecer diseño: aparece el modal de advertencia y, al confirmar, vuelve al layout
  predeterminado (AC-EDT-019).
- Selector de ancho discreto (incluida la corrección para incluir "2 columnas", ver abajo).

### Ajuste menor encontrado durante el smoke test

El selector de ancho (`WidthHeightControls.jsx`) solo ofrecía 3/4/6/8/9/12 columnas, pero las
tarjetas KPI del layout por defecto usan `width=2` (6 por fila) — un valor válido para el backend
(`ANCHO_MIN=1`) pero no representable en el `<select>`, que mostraba una opción incorrecta al
abrir el panel de un KPI. Se agregó la opción "2 columnas — 17%" a la lista.

No se probó en esta sesión (ver limitaciones en
`tests/qa/acceptance-criteria-traceability-visual-editor.md`): vista previa sin round-trip
observando la pestaña de red (AC-EDT-022) y viewport móvil real (AC-EDT-026) — el redimensionado
de ventana disponible en las herramientas de automatización no cambió el viewport efectivo de la
página.

## Resumen

| Suite | Comando | Resultado |
|---|---|---|
| Backend (Django Test) | `python manage.py test cartera` | 68/68 aprobadas |
| Frontend (Vitest) | `npm run test` | 94/94 aprobadas |
| Manual (navegador) | Ver arriba | Aprobado, con 2 correcciones aplicadas durante el smoke test |

No se marcó ningún criterio como aprobado sin una ejecución registrada en esta tabla o en
`tests/qa/acceptance-criteria-traceability-visual-editor.md`.
