# Reporte de ejecución de pruebas — Drill-down del dashboard de cartera

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
Ran 50 tests in 0.879s
OK
```

Incluye, además de la suite previa (45 pruebas), las pruebas nuevas de este cambio:

- `test_agrupa_otras_ciudades_cuando_hay_mas_de_8` (agregaciones)
- `test_filtro_multivalor_causal_otras` (API — filtro `causal=PROBLEMA,CRUCE`)
- `test_filtro_dias_vencidos_min_max` (API — drill-down de KPI de mora)
- `test_filtros_desconocidos_se_ignoran_sin_error` (API — parámetros no reconocidos no alteran el resultado ni producen error)
- `test_coherencia_entre_grafico_de_ciudad_y_detalle` (API — AC-CAR-008)

## Frontend

Comando:

```bash
cd frontend
npm run test
```

Resultado:

```
Test Files  10 passed (10)
Tests  36 passed (36)
```

Archivos de prueba nuevos/actualizados en este cambio:

- `CarteraVencidaPorCiudadChart.test.jsx` (AC-CAR-001, 002, 004, 012)
- `PortfolioDetailPanel.test.jsx` (AC-CAR-007, 018)
- `RecuperadorCausalMatrix.test.jsx` (AC-CAR-006, 013, 016)
- `CausalesChart.test.jsx` (AC-CAR-005)
- `RecuperadoresChart.test.jsx` (render, AC-CAR-014 parcial)
- `DetalleTable.test.jsx` (estados de carga/sin resultados/error — AC-CAR-010)
- `KpiRow.test.jsx` (actualizado: AC-CAR-006, 013, 017)

## Verificación manual (navegador)

Realizada con Chrome vía las herramientas de automatización, contra el backend/frontend reales
y el archivo sintético `backend/cartera/tests/fixtures/cartera_ejemplo.xlsx` (sin datos reales).
Ver el detalle y las capturas en la sección "Smoke test" de este mismo directorio y en el
`README.md`. Cubrió específicamente lo que no es automatizable con Vitest/jsdom:

- Tooltip del gráfico de pastel al pasar el cursor (AC-CAR-003).
- Clic en una barra de `RecuperadoresChart` (AC-CAR-014).
- Clic en un segmento apilado de `RecuperadorCausalChart` (AC-CAR-015).
- Apariencia visual del panel lateral (Offcanvas) y de los chips de filtros activos.

## Resumen

| Suite | Comando | Resultado |
|---|---|---|
| Backend (Django Test) | `python manage.py test cartera` | 50/50 aprobadas |
| Frontend (Vitest) | `npm run test` | 36/36 aprobadas |
| Manual (navegador) | Ver arriba | Aprobado, sin hallazgos |

No se marcó ningún criterio como aprobado sin una ejecución registrada en esta tabla o en la
matriz de trazabilidad (`acceptance-criteria-traceability.md`).
