# Dashboard de Cartera

Aplicación web para cargar un Excel de cartera de clientes, validar su estructura, mapear
columnas, procesarlo y generar un dashboard ejecutivo con KPIs, gráficos, filtros, tabla de
detalle y exportación.

![KPIs y filtros del dashboard](docs/dashboard-kpis.jpg)
![Gráfico de pastel de cartera vencida por ciudad](docs/dashboard-pastel-ciudad.jpg)
![Panel de detalle del drill-down](docs/dashboard-drilldown-panel.jpg)

*(Capturas generadas con el archivo sintético de pruebas `backend/cartera/tests/fixtures/cartera_ejemplo.xlsx`, sin datos reales de clientes.)*

## Objetivo

Permitir que un usuario no técnico cargue un archivo Excel de cartera, corrija manualmente el
mapeo de columnas si algún encabezado tiene un nombre distinto al esperado, y obtenga de forma
automática: cartera vencida/no vencida, mora por antigüedad (120/360 días), top 10 clientes,
cartera vencida por ciudad (gráfico de pastel), ranking de recuperadores, estado de la cartera
por causal y una matriz cruzada de recuperador × causal — todo filtrable, exportable y, además,
**interactivo**: cualquier gráfico, tarjeta KPI o celda de la matriz se puede seleccionar para
abrir el detalle de los registros que lo componen (ver `docs/dashboard.md`).

## Arquitectura

- **Frontend**: React 19 (Vite) + React-Bootstrap + Recharts + Axios. `frontend/`
- **Backend**: Django 5 + Django REST Framework (patrón MVT). `backend/`
- **Procesamiento de Excel**: pandas + openpyxl (.xlsx) + xlrd (.xls)
- **Base de datos**: SQL Server (vía `mssql-django` + `pyodbc`)
- **Pruebas backend**: Django Test (`APITestCase` / `TestCase`)
- **Pruebas frontend**: Vitest + React Testing Library
- **Casos de aceptación**: Gherkin (`tests/qa/dashboard_cartera.feature`,
  `tests/qa/features/dashboard-portfolio-drilldown.feature`)

Cada carga de Excel se valida y se inserta en SQL Server (`CargaArchivo` + `RegistroCartera`,
en lotes de ~2000 filas). Los endpoints de consulta (KPIs, gráficos, tabla) leen desde la base
—no vuelven a parsear el Excel— y usan pandas únicamente para las agregaciones, de modo que
cambiar la fecha de corte o un filtro no requiere reprocesar el archivo original.

**Drill-down**: no existe (ni existía) un router de páginas en el frontend, así que el detalle
de cualquier selección se implementó como un panel lateral reutilizable (`Offcanvas`), no como
una ruta nueva. El contrato de filtros (`useDrilldown`) y el mapeo gráfico→filtro completos
están documentados en `docs/dashboard.md`.

### Estructura de carpetas

```
backend/
  config/                 # settings, urls, wsgi
  cartera/
    models.py             # CargaArchivo, RegistroCartera
    views.py, urls.py, serializers/exceptions
    services/             # excel_reader, column_mapper, validators, ingest,
                           # calculator, aggregations, export_service, filters
    utils/                # normalization.py, dates.py
    management/commands/clean_temp_uploads.py
    tests/                # Django Test + fixture sintético

frontend/
  src/
    pages/CarteraDashboardPage.jsx
    components/{upload,mapping,kpi,charts,filters,table,drilldown}/
    hooks/useDrilldown.jsx, useDetalleCartera.js, useCarteraDashboard.js
    services/, utils/, tests/

tests/
  qa/dashboard_cartera.feature
  qa/features/dashboard-portfolio-drilldown.feature
  qa/acceptance-criteria-traceability.md
  qa/test-execution-report.md
docs/                     # dashboard.md, api-reference.md, capturas
```

## Dependencias

**Backend** (`backend/requirements.txt`): Django, djangorestframework, django-cors-headers,
mssql-django, pyodbc, pandas, openpyxl, xlrd, python-dateutil, python-dotenv.

**Frontend** (`frontend/package.json`): react, react-dom, react-bootstrap, bootstrap, recharts,
axios; devDependencies: vite, vitest, @testing-library/react, @testing-library/jest-dom,
@testing-library/user-event, jsdom.

## Instalación

### Requisitos previos

- Python 3.11+
- Node.js 20+ / npm
- SQL Server accesible (local, Docker o remoto) y **ODBC Driver 17 for SQL Server** instalado.
- Una base de datos ya creada (el proyecto no la crea, solo las tablas vía migraciones).

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # y completar credenciales reales
python manage.py migrate
python manage.py runserver 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173, con proxy /api -> :8000
```

## Variables de entorno (`backend/.env`)

| Variable | Descripción |
|---|---|
| `DEBUG` | `True`/`False` |
| `SECRET_KEY` | Clave secreta de Django |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma |
| `DB_ENGINE` | `mssql` (por defecto) o `sqlite` para desarrollo sin SQL Server |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a SQL Server |
| `DB_ENCRYPT`, `DB_TRUST_SERVER_CERTIFICATE` | Opciones de cifrado ODBC (`Encryption: Optional` ≈ `DB_ENCRYPT=no` + `DB_TRUST_SERVER_CERTIFICATE=yes`) |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos para el frontend |
| `UPLOAD_MAX_SIZE_BYTES` | Tamaño máximo de archivo de carga |

Con `DB_ENGINE=sqlite` el proyecto corre sin SQL Server (útil para probar rápido); el resto del
código no cambia, ya que Django ORM abstrae el motor.

## Estructura esperada del Excel

27 columnas (ver `cartera/services/column_mapper.py`):

```
Sucursal, Lugar Geográfico, Zona, Alterno Cliente, Código cle, Cliente,
Vendedor / Ejecutivo Ventas, Estado Cliente, Ruc Cliente, Telefono, Dirección,
Número de Documento, Fecha de Vencimiento, Fecha de Emisión, Saldo, Articulo,
VENCE, OBSERVACION, Mes, Tipo de Venta, Causal, Producto, Fecha compromiso pago,
Observaciones, Tipo Cartera, Vendedor 3, Dias credito
```

### Columnas obligatorias

| Dato | Columna por defecto |
|---|---|
| Cliente | `Cliente` |
| Identificador | `Ruc Cliente` |
| Documento | `Número de Documento` |
| Fecha de vencimiento | `Fecha de Vencimiento` |
| Fecha de emisión | `Fecha de Emisión` |
| Saldo | `Saldo` |
| Ciudad | `Lugar Geográfico` |
| Recuperador | `Vendedor 3` |
| Causal | `Causal` |

El reconocimiento de encabezados ignora mayúsculas/minúsculas, tildes, espacios extra y guiones
bajos (`cartera/utils/normalization.py` + `column_mapper.py`), y **nunca** sugiere
`Vendedor / Ejecutivo Ventas` como recuperador — solo `Vendedor 3` se autodetecta para ese
campo, aunque el usuario puede reasignarlo manualmente en el mapeo si así lo decide.

## Reglas de cálculo

- **Identificador único de cliente**: `Ruc Cliente` → si vacío, `Código cle` → si vacío, nombre
  normalizado de `Cliente`.
- **Los espacios vacíos de la columna `Causal` se interpretan como cartera sin gestión**
  (`SIN GESTIÓN`), no se ocultan.
- **Recuperador vacío** → `SIN RECUPERADOR ASIGNADO`. **Ciudad vacía** → `SIN CIUDAD`.
- **Vencida**: `Fecha de Vencimiento <= fecha de corte` y `Saldo > 0`.
- **No vencida**: `Fecha de Vencimiento > fecha de corte` y `Saldo > 0`.
- **Días vencidos**: `fecha de corte - Fecha de Vencimiento` (recalculado siempre, no se usa la
  columna `VENCE` del Excel).
- **Mayor a 120 / 360 días**: días vencidos > 120 / > 360, con `Saldo > 0`.
- Saldos no convertibles a número se **descartan** de los cálculos (y se listan en el resumen
  de validación); saldos en cero o negativos se conservan y se clasifican como `SALDO CERO` /
  `SALDO A FAVOR`.

## Fecha de corte

Por defecto, el **último día calendario del mes anterior** a la fecha del servidor
(`cartera/utils/dates.py:fecha_corte_por_defecto`). Es editable desde la interfaz; al cambiarla,
todos los KPIs, gráficos, la matriz y la tabla se recalculan sin volver a leer el Excel.

## Endpoints

```
POST   /api/cartera/validar-archivo
POST   /api/cartera/procesar
GET    /api/cartera/resumen/<carga_id>
GET    /api/cartera/top-clientes/<carga_id>
GET    /api/cartera/pareto-ciudades/<carga_id>
GET    /api/cartera/recuperadores/<carga_id>
GET    /api/cartera/causales/<carga_id>
GET    /api/cartera/recuperadores-causales/<carga_id>?formato=chart|matriz&metrica=saldo|documentos|clientes
GET    /api/cartera/detalle/<carga_id>?page=&page_size=&buscar=&ordering=&<filtros>
GET    /api/cartera/exportar/<carga_id>?formato=xlsx|csv&tipo=detalle|errores
DELETE /api/cartera/archivo/<carga_id>

GET    /api/dashboards/<dashboard_id>/layout
PUT    /api/dashboards/<dashboard_id>/layout
POST   /api/dashboards/<dashboard_id>/layout/reset
GET    /api/dashboards/<dashboard_id>/versions
```

Todos los GET de agregaciones aceptan como query params opcionales: `fecha_corte`, `cliente`,
`ciudad`, `zona`, `sucursal`, `recuperador`, `causal`, `estado_cartera`, `rango_mora`,
`producto`, `articulo`, `tipo_venta`, `estado_cliente`, y (nuevos, para el drill-down)
`dias_vencidos_min`/`dias_vencidos_max`. `ciudad`/`causal`/`recuperador`/etc. aceptan una lista
separada por comas (`ciudad=QUITO,CUENCA`) para filtrar por "cualquiera de estos" — lo usa el
drill-down de la categoría "Otras ciudades"/"OTRAS". Ver `docs/api-reference.md` para el detalle
completo, incluida la nueva forma de respuesta de `/pareto-ciudades` (gráfico de pastel).

## Editor visual del dashboard

El botón **"Editar dashboard"** (visible según permisos, ver abajo) activa un modo de edición que
permite personalizar la presentación del dashboard sin tocar los datos ni las consultas.

### Modo edición

Al activarlo, cada componente (KPI, gráfico, filtro, mensaje, alerta, tabla o título) muestra un
borde punteado con: una manija de arrastre (⠿, accesible por teclado vía `dnd-kit`), botones
`« ‹ › »` para mover el componente al inicio/arriba/abajo/al final (alternativa accesible al
arrastre, siempre disponible), un engranaje que abre el panel de configuración, y un botón
Ocultar/Mostrar. La barra superior ofrece **Vista previa** (oculta el chrome de edición para ver
el resultado final, sin ninguna llamada al backend), **Restablecer diseño**, **Cancelar** y
**Guardar cambios**; cancelar con cambios sin guardar y restablecer piden confirmación en un
modal (nunca `window.confirm`).

### Personalización por componente

El panel de configuración (engranaje) permite editar, por componente: **título**, **descripción**,
**ancho** (selector discreto: 2/3/4/6/8/9/12 de 12 columnas — no hay arrastre libre de bordes en
píxeles, que sería menos accesible y podría producir superposiciones), **alto** (presets
Pequeño/Mediano/Grande o un valor personalizado en píxeles, mínimo 60px) y **colores** (principal,
vencido, no vencido, sin gestión, texto y fondo — validados como hex `#RGB`/`#RRGGBB` o `rgba(...)`
tanto en frontend como en backend). El panel de filtros tiene además su propia lista de
reordenamiento (mover arriba/abajo) para sus 16 campos, independiente de la cuadrícula principal
de componentes. **No** se puede cambiar el tipo de gráfico (Recharts con tipo fijo por
componente) — ver "Fuera de alcance" abajo.

### Sistema de cuadrícula

`EditableGrid` usa un único contenedor `flex-wrap`: cada componente reserva una fracción de
`ancho/12` y el propio `flex-wrap` acomoda todo automáticamente al reordenar, ocultar o cambiar de
ancho — no existen coordenadas fila/columna que mantener a mano, así que **nunca puede haber
superposición ni huecos que reorganizar**. El `order` de cada componente es una secuencia global
única (no se reinicia por fila); `row` se recalcula solo para guardarlo en el backend
(auditoría/compatibilidad de esquema) y no gobierna el renderizado.

### Persistencia, auditoría y versionado

"Guardar cambios" envía todo el layout como una única operación atómica (no hay endpoint por
componente) junto con un nombre libre para auditoría (por defecto "Anónimo", ya que no hay
sistema de usuarios). El backend valida la versión enviada contra la versión actual guardada: si
alguien más guardó primero, responde `409` y el frontend ofrece recargar la configuración más
reciente en vez de sobrescribirla silenciosamente. Cada guardado incrementa la versión y registra
en `DashboardAuditLog` quién hizo el cambio, cuándo, y el tipo de cambio por componente (orden,
tamaño, color, texto, visibilidad, restablecido). "Restablecer diseño" reemplaza la configuración
por el diseño predeterminado (definido en código en
`backend/cartera/services/dashboard_layout.py`, no en datos de migración) para **todos los
usuarios**, y también queda registrado en el historial — no se puede deshacer.

### Permisos

Los 7 permisos (`dashboard.view`, `dashboard.edit`, `dashboard.layout.edit`,
`dashboard.component.style`, `dashboard.component.create`, `dashboard.component.delete`,
`dashboard.configuration.reset`) están modelados como constantes y se verifican en un único punto
en cada capa: `usePermisos()` en el frontend y `cartera/permisos.py` en el backend. **La
aplicación no tiene sistema de autenticación**, así que hoy ese único punto concede todos los
permisos sin verificar nada — pero como todo el editor (frontend y backend) consulta
exclusivamente esa función, conectar roles/usuarios reales en el futuro es cambiar esa función,
no la lógica de cada componente o endpoint.

### Fuera de alcance (documentado explícitamente, no simulado)

- **Cambio de tipo de gráfico**: los gráficos son componentes React (Recharts) con tipo fijo; el
  campo `chart_type` está modelado en el esquema para el futuro pero la UI no ofrece cambiarlo.
- **Restaurar una versión anterior** desde el historial de auditoría: se puede consultar
  (`GET /api/dashboards/<id>/versions`) pero no hay una acción de "volver a esta versión" en la UI.
- **Layouts por rol o por usuario** (`scope=POR_ROL`/`POR_USUARIO`): el modelo los contempla pero
  solo `GENERAL` está implementado, coherente con la ausencia de autenticación real.

## Ejecución de pruebas

```bash
# Backend (68 pruebas: normalización, cálculo, agregaciones, validadores, filtros de
# drill-down, API completa, layout/permisos/auditoría del editor visual)
cd backend
python manage.py test cartera

# Frontend (94 pruebas: carga de archivo, mapeo, KPIs, formato, gráficos interactivos,
# panel de drill-down, estados de carga/error/sin-resultados, editor visual del dashboard)
cd frontend
npm run test
```

Los criterios de aceptación en Gherkin están en `tests/qa/dashboard_cartera.feature`,
`tests/qa/features/dashboard-portfolio-drilldown.feature` y
`tests/qa/features/dashboard-visual-editor.feature` (documentan el comportamiento esperado; están
cubiertos por las pruebas automatizadas de arriba y, para lo que no es automatizable en jsdom —
hover de tooltip, clics sobre marcas SVG de Recharts, arrastre real con `dnd-kit` —, por
verificación manual en navegador). El detalle criterio-por-criterio y qué se ejecutó realmente
está en `tests/qa/acceptance-criteria-traceability.md`,
`tests/qa/acceptance-criteria-traceability-visual-editor.md` y
`tests/qa/test-execution-report.md`.

## Seguridad

Extensión + firma de archivo validadas (bloquea `.xlsm`/macros), nombre de archivo temporal
aleatorio (UUID, nunca el original), `carga_id` validado como UUID existente antes de cualquier
operación de archivo, límite de tamaño configurable, sanitización de celdas que empiecen con
`= + - @` al exportar (anti inyección de fórmulas), borrado del archivo temporal tras procesar o
al eliminar la carga. El comando `python manage.py clean_temp_uploads --horas N` elimina
archivos temporales huérfanos (cargas validadas pero nunca procesadas).

## Limitaciones conocidas

- **Sin autenticación**: no se implementó login (no estaba en el alcance solicitado). Cada
  carga se identifica por un UUID no adivinable, pero no hay aislamiento real multi-usuario. Por
  esto, los criterios de aceptación de permisos del drill-down (`AC-CAR-009`, rechazo 401/403)
  están marcados como "No aplica" en `tests/qa/acceptance-criteria-traceability.md`, no como
  implementados — fabricar una capa de permisos falsa hubiera sido peor que dejarlo documentado.
- **Teclado en marcas SVG**: los sectores/barras/segmentos de Recharts no son focalizables de
  forma nativa. El drill-down por teclado funciona en las tarjetas KPI, las celdas de la matriz
  y las leyendas-lista del pastel y de causales; `RecuperadoresChart`, `TopClientesChart` y
  `RecuperadorCausalChart` solo abren su detalle con mouse/touch por ahora (ver
  `docs/dashboard.md`).
- **Procesamiento síncrono**: la carga se inserta en SQL Server en lotes dentro del mismo
  request HTTP (no hay cola de tareas tipo Celery); el frontend muestra un spinner mientras
  dura la operación. Para archivos de cientos de miles de filas esto sigue siendo del orden de
  segundos, pero un progreso porcentual en tiempo real requeriría infraestructura adicional no
  incluida en este alcance.
- **Filtros de texto libre** (ciudad, zona, sucursal, producto, artículo, tipo de venta, estado
  del cliente) requieren coincidencia exacta (insensible a mayúsculas); no hay autocompletado
  con los valores reales del archivo cargado.
- El archivo Excel real usado para validar esta implementación (con datos reales de clientes)
  **no se incluyó en el repositorio** por privacidad; las pruebas automatizadas usan
  `backend/cartera/tests/fixtures/cartera_ejemplo.xlsx`, un archivo sintético con la misma
  estructura de 27 columnas y datos ficticios que cubren los casos límite de la especificación.
- **Editor visual sin autenticación real**: como el resto de la app, los permisos del editor
  (`dashboard.edit`, `dashboard.configuration.reset`, etc.) están modelados pero hoy se conceden
  todos sin verificar identidad — ver la sección "Permisos" arriba. Por eso los escenarios de
  rechazo por rol en `dashboard-visual-editor.feature` se prueban simulando el punto único de
  verificación (`usePermisos`/`permisos.tiene_permiso`) devolviendo `false`, no con un login real.
- **Editor visual en pantalla angosta (móvil)**: no se verificó en un viewport móvil real durante
  esta sesión (ver limitación en
  `tests/qa/acceptance-criteria-traceability-visual-editor.md`, AC-EDT-026); queda como
  verificación pendiente.
- **Restaurar una versión anterior del historial de auditoría** no está implementado en la UI
  (solo consultar el historial); ver "Fuera de alcance" en la sección del editor visual.
