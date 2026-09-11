# Módulo: cartera

Hereda `../CLAUDE.md` y `@.claude/rules/security.md` (upload/exportación) y
`@.claude/rules/dashboards.md` (editor visual, compartido con el frontend).

## Responsabilidad

App original del proyecto (pre-integración con skelleton_base): carga y validación de Excel de
cartera, cálculo de KPIs/agregaciones, editor visual de dashboards por área, y el contrato de
error usado por **toda** la API (`exceptions.py`, ver raíz del repo).

## Estructura

- `models.py` — `Dashboard` (un dashboard por área; `parent` self-FK para pestañas, máx. 5 por
  familia; `roles_editores`/`roles_lectores` M2M a `Group` para ACL por dashboard, vacío = cae al
  permiso global `dashboard.view`), `CargaArchivo` (pk UUID), `RegistroCartera`,
  `FilaArchivoHistorico`, `ColumnaHistorica`, `DashboardLayout`/`DashboardComponent`/
  `DashboardAuditLog`.
- `services/` — `excel_reader`, `column_mapper`, `validators`, `ingest`, `calculator`,
  `aggregations`, `export_service`, `filters`, `dashboard_layout`, `historico`, `plantilla`,
  `carga_archivos` (releer el archivo de una carga), `reproceso` (recalcular contenido almacenado).
- `permisos.py` — resolución de permisos legacy + control de acceso por-dashboard.
- `management/commands/clean_temp_uploads.py` — `python manage.py clean_temp_uploads --horas N`.
- `services/directorio_cartera.py` + `management/commands/sembrar_directorio_cartera.py` — el
  "Dashboard Directorio" es la **excepción declarada** del proyecto: no usa las 13 posiciones de la
  plantilla sino 7 componentes propios (4 KPI, gráfico de antigüedad, tabla de cumplimiento de
  metas, tabla de concentración), con sus propios anchos, altos y colores. Las 13 de fábrica quedan
  ocultas y bloqueadas. `python manage.py sembrar_directorio_cartera --archivo X.xlsx [--aplicar]`
  lo reconstruye con datos reales (simula por defecto). La estructura replica la que sembró la
  migración `0021`; lo que cambia es que el contenido se calcula de verdad en vez de ser ficticio.
- `management/commands/reprocesar_dashboards.py` — `python manage.py reprocesar_dashboards
  [--aplicar] [--dashboard ID] [--detalle]`. **Simula por defecto**: sin `--aplicar` no escribe
  nada. Recalcula `DashboardComponent.content` con el código de cálculo vigente, contra la misma
  carga y la misma fecha de corte, para que una corrección del núcleo de cálculo llegue a los
  dashboards que ya existen (el campo es almacenado, nadie los recalcula solo).

## Contrato de error (global, no solo de este módulo)

`CarteraError(mensaje, codigo='X', detalles={})` + `cartera_exception_handler` es el
`EXCEPTION_HANDLER` de **todo** `REST_FRAMEWORK` (`config/settings.py`). Cualquier app del backend
lanza `CarteraError` para un 400 de negocio estructurado — no crees un segundo contrato de error.

## Permisos (`permisos.py`)

Los 10 codenames `dashboard.*` (`DASHBOARD_VIEW`, `DASHBOARD_EDIT`, `DASHBOARD_LAYOUT_EDIT`,
`DASHBOARD_COMPONENT_STYLE/CREATE/DELETE`, `DASHBOARD_CONFIGURATION_RESET`, `DASHBOARD_CREAR/
EDITAR/ELIMINAR`) **son** los mismos strings que `apps.permissions.catalog.PERMISSION_CATALOG`
(módulo `dashboard`) — no son un sistema paralelo. No renombres uno sin el otro.
`puede_administrar_acceso(request, dashboard_id)` es intencionalmente dueño-o-superusuario
solamente, sin caer a ningún permiso del catálogo (ni `dashboard.editar`) — no lo relajes sin
confirmar el motivo con el usuario.

## Reglas de cálculo (resumen — detalle completo en `../../README.md`)

- Identificador único de cliente: `Ruc Cliente` → si vacío, `Código cle` → si vacío, nombre
  normalizado.
- Vencida: `Fecha de Vencimiento <= fecha de corte` y `Saldo > 0`. Días vencidos siempre
  recalculados desde las fechas — nunca se usa la columna `VENCE` del Excel.
- Recuperador vacío → `SIN RECUPERADOR ASIGNADO`; ciudad vacía → `SIN CIUDAD`; causal vacía →
  `SIN GESTIÓN` (se muestra, no se oculta).
- Fecha de corte por defecto: último día calendario del mes anterior
  (`utils/dates.py:fecha_corte_por_defecto`), editable sin reprocesar el Excel.

## Evita

- IMPORTANT: `plantilla.aplicar_mapeo` **borra y recrea** los 13 componentes
  (`dashboard_layout._escribir_componentes`), así que ancho, alto, colores y `chart_type` vuelven a
  los valores de fábrica de la plantilla. No la uses para "recalcular" un dashboard existente —
  para eso está `services/reproceso.py`, que solo toca `content`.
- No reproceses el Excel original para servir una consulta — los endpoints de agregación leen de
  `RegistroCartera` (ya insertado en SQL Server), pandas se usa solo para las agregaciones, no
  para volver a leer el archivo.
- No aceptes `page_size` fuera de {5,10,25,50,100} en ningún endpoint de tabla — ver
  `@.claude/rules/dashboards.md`.
- IMPORTANT: `cartera/migrations/` tiene 13 migraciones con seeds/backfills de datos reales —
  trátalas como potencialmente aplicadas en un entorno real, nunca las edites retroactivamente.

## Pruebas

`python manage.py test cartera`. Casos mínimos al tocar cálculo: saldo no numérico se descarta
(no se computa, se lista en advertencias); saldo cero/negativo se conserva y clasifica aparte;
cambio de fecha de corte no dispara nueva lectura del Excel.
