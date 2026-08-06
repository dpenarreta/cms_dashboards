import api from './api'

export function listarCargasHistoricas(dashboardId) {
  return api.get('/historico/cargas', { params: { dashboard_id: dashboardId } }).then((r) => r.data)
}

export function calcularTablaHistorica(dashboardId, columnasValor, cargaIds) {
  return api.post('/historico/tabla', {
    dashboard_id: dashboardId,
    columnas_valor: columnasValor,
    carga_ids: cargaIds || undefined,
  }).then((r) => r.data)
}

export function obtenerArchivoCarga(cargaId) {
  return api.get(`/historico/cargas/${cargaId}/archivo`).then((r) => r.data)
}
