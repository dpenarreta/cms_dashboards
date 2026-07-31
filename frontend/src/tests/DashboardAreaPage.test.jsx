import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import DashboardAreaPage from '../pages/dashboards/DashboardAreaPage'
import { useGenericDashboardBuilder } from '../hooks/useGenericDashboardBuilder'
import { useDashboardLayout } from '../hooks/useDashboardLayout'
import * as dashboardLayoutService from '../services/dashboardLayoutService'

vi.mock('../hooks/useGenericDashboardBuilder')
vi.mock('../hooks/useDashboardLayout')
vi.mock('../services/dashboardLayoutService')

const FASE = { CARGA: 'CARGA', ALIAS: 'ALIAS', RECOMENDACIONES: 'RECOMENDACIONES' }

function builderBase(overrides = {}) {
  return {
    FASE,
    fase: FASE.CARGA,
    archivoInfo: null,
    columnas: [],
    aliases: {},
    utilizables: {},
    recomendaciones: [],
    agregadas: new Set(),
    cargando: false,
    error: null,
    subirYValidar: vi.fn(),
    cambiarHoja: vi.fn(),
    actualizarAlias: vi.fn(),
    actualizarUtilizable: vi.fn(),
    confirmarAliases: vi.fn(),
    volverAAlias: vi.fn(),
    agregarGrafica: vi.fn().mockResolvedValue({ ok: true }),
    limpiar: vi.fn(),
    ...overrides,
  }
}

function layoutBase(overrides = {}) {
  return {
    layoutGuardado: { version: 1, components: [] },
    borrador: [],
    modoEdicion: false,
    vistaPrevia: false,
    seleccionado: null,
    cargando: false,
    error: null,
    conflicto: null,
    setSeleccionado: vi.fn(),
    activarEdicion: vi.fn(),
    cancelar: vi.fn(),
    alternarVistaPrevia: vi.fn(),
    actualizarComponente: vi.fn(),
    actualizarContenido: vi.fn(),
    actualizarEstilos: vi.fn(),
    moverComponente: vi.fn(),
    reordenarPorIds: vi.fn(),
    guardar: vi.fn(),
    restablecer: vi.fn(),
    recargarPorConflicto: vi.fn(),
    hayCambiosSinGuardar: vi.fn(() => false),
    recargar: vi.fn(),
    ...overrides,
  }
}

const KPI_COMPONENTE = {
  component_id: 'total-ventas', type: 'kpi', chart_type: '', row: 1, order: 1, width: 3, height: 180,
  is_visible: true, content: { titulo: 'Total ventas', valor: 1234 }, styles: {}, config: {},
}

const CHART_COMPONENTE = {
  component_id: 'ventas-por-ciudad', type: 'chart', chart_type: 'bar', row: 1, order: 2, width: 6, height: 420,
  is_visible: true, content: { titulo: 'Ventas por ciudad', categorias: ['Quito', 'Guayaquil'], valores: [100, 50] }, styles: {}, config: {},
}

const RECOMENDACION_KPI = {
  id: 'Saldo::total', tipo_grafica: 'kpi', columna_valor: 'Saldo', columna_categoria: null, categorias_unicas: null,
}

function renderPagina(dashboardId = 'finanzas') {
  return render(
    <MemoryRouter initialEntries={[`/app/dashboards/${dashboardId}`]}>
      <Routes>
        <Route path="/app/dashboards/:dashboardId" element={<DashboardAreaPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('DashboardAreaPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    dashboardLayoutService.obtenerDashboardsAutorizados.mockResolvedValue([
      { dashboard_id: 'finanzas', name: 'Finanzas', area: 'Finanzas y Contabilidad' },
    ])
  })

  it('muestra el nombre y el área del dashboard, resueltos por dashboard_id', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()

    expect(await screen.findByRole('heading', { name: 'Finanzas' })).toBeInTheDocument()
    expect(screen.getByText(/Finanzas y Contabilidad/)).toBeInTheDocument()
    expect(useDashboardLayout).toHaveBeenCalledWith('finanzas')
  })

  it('dashboard sin componentes: muestra la zona de carga de archivo (no el pipeline fijo de cartera)', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({ fase: FASE.CARGA }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByTestId('input-archivo')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cargar otro archivo' })).not.toBeInTheDocument()
  })

  it('dashboard sin componentes: muestra la plantilla ilustrativa debajo de la zona de carga', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({ fase: FASE.CARGA }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByLabelText('Vista previa ilustrativa de un dashboard')).toBeInTheDocument()
    expect(screen.getByText('Título del Dashboard')).toBeInTheDocument()
  })

  it('"Cargar otro archivo" en un dashboard que ya tiene componentes no muestra la plantilla ilustrativa', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    expect(screen.getByTestId('input-archivo')).toBeInTheDocument()
    expect(screen.queryByLabelText('Vista previa ilustrativa de un dashboard')).not.toBeInTheDocument()
  })

  it('en fase ALIAS, muestra las columnas detectadas para confirmar su alias', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.ALIAS,
      columnas: [
        { nombre: 'Saldo', tipo: 'numerico', apta_para_valor: true, apta_para_categoria: false, motivo_no_apta: '' },
        { nombre: 'Detalle', tipo: 'categorico', apta_para_valor: false, apta_para_categoria: false, motivo_no_apta: 'Todos los valores son distintos (parece un identificador).' },
      ],
      aliases: { Saldo: 'Saldo', Detalle: 'Detalle' },
      utilizables: { Saldo: true, Detalle: false },
    }))
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Columnas detectadas')).toBeInTheDocument()
    // Ninguna columna se oculta: ambas aparecen, aunque el análisis no recomiende "Detalle".
    expect(screen.getByLabelText('Alias para Saldo')).toHaveValue('Saldo')
    expect(screen.getByLabelText('Alias para Detalle')).toHaveValue('Detalle')
    expect(screen.getByLabelText('Utilizable: Saldo')).toBeChecked()
    expect(screen.getByLabelText('Utilizable: Detalle')).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Continuar' })).toBeInTheDocument()
  })

  it('el checkmark de utilizable llama a actualizarUtilizable() con la columna y el nuevo valor', async () => {
    const actualizarUtilizable = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.ALIAS,
      columnas: [{ nombre: 'Detalle', tipo: 'categorico', apta_para_valor: false, apta_para_categoria: false, motivo_no_apta: 'Parece un identificador.' }],
      aliases: { Detalle: 'Detalle' },
      utilizables: { Detalle: false },
      actualizarUtilizable,
    }))
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    await userEvent.click(screen.getByLabelText('Utilizable: Detalle'))
    expect(actualizarUtilizable).toHaveBeenCalledWith('Detalle', true)
  })

  it('"Continuar" en el paso de alias llama a confirmarAliases()', async () => {
    const confirmarAliases = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.ALIAS,
      columnas: [{ nombre: 'Saldo', tipo: 'numerico', apta_para_valor: true, apta_para_categoria: false, motivo_no_apta: '' }],
      aliases: { Saldo: 'Saldo' },
      utilizables: { Saldo: true },
      confirmarAliases,
    }))
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }))
    expect(confirmarAliases).toHaveBeenCalled()
  })

  it('en fase RECOMENDACIONES, muestra las tarjetas de recomendación con "Agregar"', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.RECOMENDACIONES,
      aliases: { Saldo: 'Saldo' },
      recomendaciones: [RECOMENDACION_KPI],
    }))
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Total de Saldo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agregar' })).toBeInTheDocument()
  })

  it('"Agregar" en una recomendación llama a agregarGrafica() con esa recomendación', async () => {
    const agregarGrafica = vi.fn().mockResolvedValue({ ok: true })
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.RECOMENDACIONES,
      aliases: { Saldo: 'Saldo' },
      recomendaciones: [RECOMENDACION_KPI],
      agregarGrafica,
    }))
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    await userEvent.click(screen.getByRole('button', { name: 'Agregar' }))
    expect(agregarGrafica).toHaveBeenCalledWith(RECOMENDACION_KPI, 'kpi')
  })

  it('"Volver a las columnas" desde las recomendaciones llama a volverAAlias()', async () => {
    const volverAAlias = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.RECOMENDACIONES,
      aliases: { Saldo: 'Saldo' },
      recomendaciones: [RECOMENDACION_KPI],
      volverAAlias,
    }))
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    await userEvent.click(screen.getByRole('button', { name: 'Volver a las columnas' }))
    expect(volverAAlias).toHaveBeenCalled()
  })

  it('incluye el botón "Conectar vista de base de datos", siempre deshabilitado', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByRole('button', { name: 'Conectar vista de base de datos' })).toBeDisabled()
  })

  it('dashboard con componentes generados: renderiza el KPI y la gráfica en el grid, no la zona de carga', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE, CHART_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Total ventas')).toBeInTheDocument()
    expect(screen.getByText('1.234')).toBeInTheDocument()
    expect(screen.getByText('Ventas por ciudad')).toBeInTheDocument()
    expect(screen.queryByTestId('input-archivo')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cargar otro archivo' })).toBeInTheDocument()
  })

  it('la descripción guardada de un KPI y de una gráfica se muestran en el grid', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({
      borrador: [
        { ...KPI_COMPONENTE, content: { ...KPI_COMPONENTE.content, descripcion: 'Suma de ventas del mes.' } },
        { ...CHART_COMPONENTE, content: { ...CHART_COMPONENTE.content, descripcion: 'Ventas agrupadas por ciudad.' } },
      ],
    }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Suma de ventas del mes.')).toBeInTheDocument()
    expect(screen.getByText('Ventas agrupadas por ciudad.')).toBeInTheDocument()
  })

  it('un componente de tipo dispersión y uno de área apilada se renderizan en el grid', async () => {
    const DISPERSION_COMPONENTE = {
      component_id: 'saldo-vs-dias-credito', type: 'chart', chart_type: 'dispersion', row: 1, order: 3, width: 6, height: 420,
      is_visible: true, content: { titulo: 'Saldo vs. Dias credito', puntos: [{ x: 100, y: 10 }] }, styles: {}, config: {},
    }
    const AREA_APILADA_COMPONENTE = {
      component_id: 'saldo-por-ciudad-y-causal', type: 'chart', chart_type: 'area_apilada', row: 1, order: 4, width: 6, height: 420,
      is_visible: true,
      content: {
        titulo: 'Saldo por ciudad y causal', categorias: ['Quito', 'Guayaquil'],
        series: [{ nombre: 'Vencido', valores: [10, 20] }],
      },
      styles: {}, config: {},
    }
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [DISPERSION_COMPONENTE, AREA_APILADA_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Saldo vs. Dias credito')).toBeInTheDocument()
    expect(screen.getByText('Saldo por ciudad y causal')).toBeInTheDocument()
  })

  it('"Cargar otro archivo" muestra la zona de carga; "Cancelar" vuelve a mostrar el grid y llama a limpiar()', async () => {
    const limpiar = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({ limpiar }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))
    expect(screen.getByTestId('input-archivo')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(limpiar).toHaveBeenCalled()
    expect(screen.getByText('Total ventas')).toBeInTheDocument()
  })

  it('"Ir al dashboard" tras agregar recomendaciones recarga el layout y vuelve a mostrar el grid', async () => {
    const recargar = vi.fn()
    const agregadas = new Set(['Saldo::total'])
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.RECOMENDACIONES,
      aliases: { Saldo: 'Saldo' },
      recomendaciones: [RECOMENDACION_KPI],
      agregadas,
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE], recargar }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))
    await userEvent.click(screen.getByRole('button', { name: 'Ir al dashboard' }))

    expect(recargar).toHaveBeenCalled()
    expect(screen.getByText('Total ventas')).toBeInTheDocument()
  })

  it('un componente oculto (is_visible=false) no se renderiza fuera del modo edición', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({
      borrador: [{ ...KPI_COMPONENTE, is_visible: false }],
    }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.queryByText('Total ventas')).not.toBeInTheDocument()
  })
})
