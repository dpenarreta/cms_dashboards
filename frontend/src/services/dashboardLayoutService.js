import { createApiClient } from './httpClient'

const api = createApiClient('/api/dashboards')

export function obtenerLayout(dashboardId) {
  return api.get(`/${dashboardId}/layout`).then((r) => r.data)
}

/** El autor del cambio lo resuelve el backend desde el usuario autenticado (nunca se envía
 * desde acá: era falsificable, ver `cartera/dashboard_views.py::_etiqueta_actor`). */
export function guardarLayout(dashboardId, { version, components }) {
  return api.put(`/${dashboardId}/layout`, { version, components }).then((r) => r.data)
}

export function restablecerLayout(dashboardId) {
  return api.post(`/${dashboardId}/layout/reset`).then((r) => r.data)
}

/** Agrega un componente de solo presentación (título o separador, panel lateral de componentes)
 * — a diferencia del resto de acciones del editor, persiste de inmediato (no pasa por el
 * borrador ni por "Guardar cambios"), igual que `carteraService.agregarComponentePersonal`. */
export function agregarComponentePresentacional(dashboardId, { tipo, anchoColumnas, zona }) {
  return api.post(`/${dashboardId}/componentes-presentacionales`, {
    tipo, ancho_columnas: anchoColumnas, zona,
  }).then((r) => r.data)
}

export function obtenerVersiones(dashboardId) {
  return api.get(`/${dashboardId}/versions`).then((r) => r.data)
}

export function obtenerDashboardsAutorizados() {
  return api.get('/authorized').then((r) => r.data)
}

export function crearDashboard({ name, area, description, contexto }) {
  return api.post('/', { name, area, description, contexto }).then((r) => r.data)
}

export function actualizarDashboard(dashboardId, { name, area, contexto }) {
  return api.patch(`/${dashboardId}/`, { name, area, contexto }).then((r) => r.data)
}

export function eliminarDashboard(dashboardId, confirmationName) {
  return api.delete(`/${dashboardId}/`, { data: { confirmation_name: confirmationName } }).then((r) => r.data)
}

export function obtenerPestanas(dashboardId) {
  return api.get(`/${dashboardId}/pestanas`).then((r) => r.data)
}

export function crearPestana(dashboardId, { name }) {
  return api.post(`/${dashboardId}/pestanas`, { name }).then((r) => r.data)
}

/** Vista/procedimiento de la conexión externa "por defecto" configurada para ESTE dashboard/
 * pestaña puntual (`Dashboard.fuente_bd_tipo`/`fuente_bd_nombre`, ver
 * `backend/cartera/services/db_source.py`) — `{tipo: '', nombre: ''}` si no tiene ninguna. Separado
 * de `actualizarDashboard` (nombre/área/contexto) a propósito, ver docstring de
 * `DashboardFuenteBDView` en el backend. */
export function obtenerFuenteBD(dashboardId) {
  return api.get(`/${dashboardId}/fuente-bd`).then((r) => r.data)
}

export function actualizarFuenteBD(dashboardId, { tipo, nombre, parametros, fechaFormato, frecuenciaActualizacion }) {
  return api.put(`/${dashboardId}/fuente-bd`, {
    tipo, nombre, parametros, fecha_formato: fechaFormato, frecuencia_actualizacion: frecuenciaActualizacion,
  }).then((r) => r.data)
}

export function borrarDatosDashboard(dashboardId, confirmationName) {
  return api.post(`/${dashboardId}/borrar-datos`, { confirmation_name: confirmationName }).then((r) => r.data)
}

export function obtenerAcceso(dashboardId) {
  return api.get(`/${dashboardId}/acceso`).then((r) => r.data)
}

export function actualizarAcceso(dashboardId, { rolesEditores, rolesLectores }) {
  return api.put(`/${dashboardId}/acceso`, { roles_editores: rolesEditores, roles_lectores: rolesLectores }).then((r) => r.data)
}

export function reasignarDueno(dashboardId, ownerId) {
  return api.patch(`/${dashboardId}/dueno`, { owner_id: ownerId }).then((r) => r.data)
}

// Timeout de las llamadas con IA: más largo que el resto porque incluyen una llamada a un LLM
// externo (Gemini) — el backend le da a esa llamada hasta 45s (`dashboard_interpretation.py`,
// `_TIMEOUT_SEGUNDOS`); acá se deja margen por encima de eso (60s), no el mismo valor, para que el
// backend siempre tenga chance de responder con su propio error de timeout antes de que el
// frontend aborte la request por su cuenta.
const _TIMEOUT_IA_MS = 60000

/** Interpretación completa del dashboard generada por IA (`services/dashboard_interpretation.py`). */
export function generarInterpretacion(dashboardId) {
  return api.post(`/${dashboardId}/interpretacion`, {}, { timeout: _TIMEOUT_IA_MS }).then((r) => r.data)
}

/** "Hallazgos clave" por componente generados por IA, un único llamado batch para todo el
 * dashboard (`{hallazgos: {component_id: texto}}`) — mismo timeout que `generarInterpretacion` por
 * la misma razón. Reemplaza progresivamente, componente por componente, el texto generado con
 * reglas fijas (`utils/hallazgosClave.js`), que sigue siendo el fallback instantáneo mientras esta
 * llamada resuelve o si falla (ver `HallazgosClaveCard.jsx`). */
export function generarHallazgosIA(dashboardId) {
  return api.post(`/${dashboardId}/hallazgos-ia`, {}, { timeout: _TIMEOUT_IA_MS }).then((r) => r.data)
}
