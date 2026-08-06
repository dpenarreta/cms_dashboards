import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import DashboardAreaPage from '../pages/dashboards/DashboardAreaPage'
import { useGenericDashboardBuilder } from '../hooks/useGenericDashboardBuilder'
import { useDashboardLayout } from '../hooks/useDashboardLayout'
import * as dashboardLayoutService from '../services/dashboardLayoutService'
import * as historicoService from '../services/historicoService'
import * as carteraService from '../services/carteraService'
import { useAuth } from '../context/AuthContext'

vi.mock('../hooks/useGenericDashboardBuilder')
vi.mock('../hooks/useDashboardLayout')
vi.mock('../services/dashboardLayoutService')
vi.mock('../services/historicoService')
vi.mock('../services/carteraService')
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const FASE = { CARGA: 'CARGA', RENOMBRAR: 'RENOMBRAR', VALORES_EN_BLANCO: 'VALORES_EN_BLANCO', MAPEO: 'MAPEO' }

function builderBase(overrides = {}) {
  return {
    FASE,
    fase: FASE.CARGA,
    archivoInfo: null,
    columnasOriginales: [],
    aliases: {},
    columnas: [],
    mapeo: {},
    datos: {},
    columnasConBlancos: [],
    valoresBlancos: {},
    columnasHistoricas: [],
    columnasHistoricasFinales: [],
    cargando: false,
    cargandoPreview: false,
    error: null,
    subirYValidar: vi.fn(),
    cambiarHoja: vi.fn(),
    actualizarAlias: vi.fn(),
    cancelarRenombrado: vi.fn(),
    confirmarRenombrado: vi.fn(),
    actualizarValorBlanco: vi.fn(),
    confirmarValoresBlancos: vi.fn(),
    cancelarValoresBlancos: vi.fn(),
    actualizarColumnaHistorica: vi.fn(),
    inicializarColumnasHistoricas: vi.fn(),
    actualizarMapeoSlot: vi.fn(),
    cancelarMapeo: vi.fn(),
    confirmarMapeo: vi.fn().mockResolvedValue({ ok: true }),
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
  component_id: 'kpi-1', type: 'kpi', chart_type: '', row: 1, order: 1, width: 3, height: 180,
  is_visible: true, content: { titulo: 'Total ventas', valor: 1234 }, styles: {}, config: {},
}

const CHART_COMPONENTE = {
  component_id: 'grafico-1', type: 'chart', chart_type: 'barras_verticales', row: 1, order: 2, width: 6, height: 420,
  is_visible: true, content: { titulo: 'Ventas por ciudad', categorias: ['Quito', 'Guayaquil'], valores: [100, 50] }, styles: {}, config: {},
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
    dashboardLayoutService.obtenerPestanas.mockResolvedValue([
      { dashboard_id: 'finanzas', name: 'Finanzas', orden: 1 },
    ])
    useAuth.mockReturnValue({ user: { permissions: [] } })
    // La página pide `columnasHistoricasConfiguradas` siempre (Tabla 4/5 la necesitan también
    // fuera del asistente de carga) — sin este default, cualquier test que no le interese esa
    // parte rompería al llamar `.then` sobre un mock sin resolver.
    historicoService.listarCargasHistoricas.mockResolvedValue({
      cargas: [], columnas_disponibles: [], columnas_historicas_configuradas: [],
    })
    // `AgregarComponentePersonalModal` (siempre montado, oculto por defecto) pide el archivo
    // actual apenas se abre — sin este default, un test que active el modal rompería al llamar
    // `.then()` sobre un mock sin resolver.
    carteraService.obtenerArchivoActualDashboard.mockResolvedValue({ disponible: false })
  })

  it('muestra el nombre y el área del dashboard, resueltos por dashboard_id', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()

    expect(await screen.findByRole('heading', { name: 'Finanzas' })).toBeInTheDocument()
    expect(screen.getByText(/Finanzas y Contabilidad/)).toBeInTheDocument()
    expect(useDashboardLayout).toHaveBeenCalledWith('finanzas')
  })

  it('sin acceso al dashboard (403 en la carga inicial), muestra el error en vez de spinnear indefinidamente', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({
      layoutGuardado: null, error: 'No tiene permiso para ver este dashboard.',
    }))
    renderPagina()

    expect(await screen.findByText('No tiene permiso para ver este dashboard.')).toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('en una pestaña que no es la raíz, el título y el área siguen siendo los de la raíz, no los de la pestaña', async () => {
    dashboardLayoutService.obtenerPestanas.mockResolvedValue([
      { dashboard_id: 'finanzas', name: 'Finanzas', orden: 1 },
      { dashboard_id: 'finanzas-2', name: 'Vista regional', orden: 2 },
    ])
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina('finanzas-2')

    expect(await screen.findByRole('heading', { name: 'Finanzas' })).toBeInTheDocument()
    expect(screen.getByText(/Finanzas y Contabilidad/)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Vista regional' })).not.toBeInTheDocument()
  })

  it('por defecto muestra el grid con las posiciones de la plantilla, no la zona de carga', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE, CHART_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Total ventas')).toBeInTheDocument()
    expect(screen.getByText('Ventas por ciudad')).toBeInTheDocument()
    expect(screen.queryByTestId('input-archivo')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cargar otro archivo' })).toBeInTheDocument()
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

  it('en fase RENOMBRAR, muestra el paso de renombrar columnas', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.RENOMBRAR,
      archivoInfo: { nombreArchivo: 'datos.xlsx', totalFilas: 10 },
      columnasOriginales: ['Saldo', 'Ciudad'],
      aliases: { Saldo: 'Saldo', Ciudad: 'Ciudad' },
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    expect(screen.getByText(/datos\.xlsx/)).toBeInTheDocument()
    expect(screen.getByLabelText('Nuevo nombre para Saldo')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continuar' })).toBeInTheDocument()
  })

  it('"Continuar" en el paso de renombrar llama a confirmarRenombrado()', async () => {
    const confirmarRenombrado = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.RENOMBRAR, columnasOriginales: ['Saldo'], aliases: { Saldo: 'Saldo' }, confirmarRenombrado,
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }))
    expect(confirmarRenombrado).toHaveBeenCalled()
  })

  it('en fase VALORES_EN_BLANCO, muestra el paso de valores en blanco', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.VALORES_EN_BLANCO,
      archivoInfo: { nombreArchivo: 'datos.xlsx', totalFilas: 20 },
      columnasConBlancos: [{ columna: 'Alterno Cliente', cantidad_en_blanco: 15, filas_ejemplo: [] }],
      columnas: [{ nombre: 'Alterno Cliente', tipo: 'vacio', apta_para_valor: false, apta_para_categoria: false }],
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    expect(screen.getByText('Valores en blanco')).toBeInTheDocument()
    expect(screen.getByText('Alterno Cliente')).toBeInTheDocument()
    expect(screen.getByLabelText('Valor de reemplazo para Alterno Cliente')).toBeInTheDocument()
  })

  it('"Continuar" en el paso de valores en blanco llama a confirmarValoresBlancos()', async () => {
    const confirmarValoresBlancos = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.VALORES_EN_BLANCO,
      columnasConBlancos: [{ columna: 'Alterno Cliente', cantidad_en_blanco: 15, filas_ejemplo: [] }],
      confirmarValoresBlancos,
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }))
    expect(confirmarValoresBlancos).toHaveBeenCalled()
  })

  it('"Cancelar" en el paso de valores en blanco llama a cancelarValoresBlancos()', async () => {
    const cancelarValoresBlancos = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.VALORES_EN_BLANCO,
      columnasConBlancos: [{ columna: 'Alterno Cliente', cantidad_en_blanco: 15, filas_ejemplo: [] }],
      cancelarValoresBlancos,
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(cancelarValoresBlancos).toHaveBeenCalled()
  })

  it('"Cancelar" en el paso de renombrar llama a cancelarRenombrado()', async () => {
    const cancelarRenombrado = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.RENOMBRAR, columnasOriginales: ['Saldo'], aliases: { Saldo: 'Saldo' }, cancelarRenombrado,
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(cancelarRenombrado).toHaveBeenCalled()
  })

  describe('advertencia de columnas históricas en el paso de renombrar', () => {
    it('sin ninguna columna histórica configurada, no muestra advertencia', async () => {
      historicoService.listarCargasHistoricas.mockResolvedValue({
        cargas: [], columnas_disponibles: [], columnas_historicas_configuradas: [],
      })
      useGenericDashboardBuilder.mockReturnValue(builderBase({
        fase: FASE.RENOMBRAR, columnasOriginales: ['Costo'], aliases: { Costo: 'Costo' },
      }))
      useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })
      await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

      expect(screen.getByLabelText('Nuevo nombre para Costo')).toBeInTheDocument()
      expect(screen.queryByText(/estaban marcadas como históricas/)).not.toBeInTheDocument()
    })

    it('con una columna histórica configurada que no está en el archivo nuevo, advierte', async () => {
      historicoService.listarCargasHistoricas.mockResolvedValue({
        cargas: [], columnas_disponibles: ['Ventas', 'Costo'], columnas_historicas_configuradas: ['Ventas', 'Costo'],
      })
      useGenericDashboardBuilder.mockReturnValue(builderBase({
        fase: FASE.RENOMBRAR, columnasOriginales: ['Costo'], aliases: { Costo: 'Costo' },
      }))
      useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })
      await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

      expect(historicoService.listarCargasHistoricas).toHaveBeenCalledWith('finanzas')
      expect(await screen.findByText(/estaban marcadas como históricas/)).toBeInTheDocument()
      expect(screen.getByText(/"Ventas"/)).toBeInTheDocument()
    })

    it('con las columnas históricas configuradas presentes en el archivo, no muestra advertencia', async () => {
      historicoService.listarCargasHistoricas.mockResolvedValue({
        cargas: [], columnas_disponibles: ['Ventas'], columnas_historicas_configuradas: ['Ventas'],
      })
      useGenericDashboardBuilder.mockReturnValue(builderBase({
        fase: FASE.RENOMBRAR, columnasOriginales: ['Ventas'], aliases: { Ventas: 'Ventas' },
      }))
      useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })
      await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

      await waitFor(() => expect(historicoService.listarCargasHistoricas).toHaveBeenCalled())
      expect(screen.queryByText(/estaban marcadas como históricas/)).not.toBeInTheDocument()
    })
  })

  it('en fase MAPEO, muestra el paso de mapeo a la plantilla', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.MAPEO,
      archivoInfo: { nombreArchivo: 'datos.xlsx', totalFilas: 10 },
      columnas: [{ nombre: 'Saldo', tipo: 'numerico', apta_para_valor: true, apta_para_categoria: false }],
      mapeo: { 'kpi-1': { disponible: true, columna_valor: 'Saldo' } },
      datos: { 'kpi-1': { titulo: 'KPI 1', valor: 1000, formato: 'numero' } },
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    // El paso de mapeo solo se muestra dentro del constructor, que arranca oculto.
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    expect(screen.getByText(/datos\.xlsx/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Aplicar a la plantilla' })).toBeInTheDocument()
  })

  it('en fase MAPEO, con una columna con blancos marcada como histórica, muestra el aviso con el badge histórico', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase({
      fase: FASE.MAPEO,
      archivoInfo: { nombreArchivo: 'datos.xlsx', totalFilas: 10 },
      columnas: [{ nombre: 'Saldo', tipo: 'numerico', apta_para_valor: true, apta_para_categoria: false }],
      mapeo: { 'kpi-1': { disponible: true, columna_valor: 'Saldo' } },
      datos: { 'kpi-1': { titulo: 'KPI 1', valor: 1000, formato: 'numero' } },
      columnasConBlancos: [{ columna: 'Saldo', cantidad_en_blanco: 5, filas_ejemplo: [] }],
      columnasHistoricasFinales: ['Saldo'],
    }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    expect(screen.getByText('Columnas con valores en blanco')).toBeInTheDocument()
    expect(screen.getByText(/usada en Tabla 4 y Tabla 5 \(histórica\)/)).toBeInTheDocument()
  })

  it('confirmar el mapeo recarga el layout y vuelve a mostrar el grid', async () => {
    const confirmarMapeo = vi.fn().mockResolvedValue({ ok: true })
    const recargar = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({ fase: FASE.MAPEO, confirmarMapeo }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE], recargar }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    await userEvent.click(screen.getByRole('button', { name: 'Aplicar a la plantilla' }))

    expect(confirmarMapeo).toHaveBeenCalled()
    expect(recargar).toHaveBeenCalled()
    expect(screen.getByText('Total ventas')).toBeInTheDocument()
  })

  it('cancelar desde el paso de mapeo llama a cancelarMapeo()', async () => {
    const cancelarMapeo = vi.fn()
    useGenericDashboardBuilder.mockReturnValue(builderBase({ fase: FASE.MAPEO, cancelarMapeo }))
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })
    await userEvent.click(screen.getByRole('button', { name: 'Cargar otro archivo' }))

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(cancelarMapeo).toHaveBeenCalled()
  })

  it('incluye el botón "Conectar vista de base de datos", siempre deshabilitado', async () => {
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase())
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByRole('button', { name: 'Conectar vista de base de datos' })).toBeDisabled()
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
      component_id: 'grafico-6', type: 'chart', chart_type: 'dispersion', row: 1, order: 3, width: 6, height: 420,
      is_visible: true, content: { titulo: 'Saldo vs. Dias credito', puntos: [{ x: 100, y: 10 }] }, styles: {}, config: {},
    }
    const AREA_APILADA_COMPONENTE = {
      component_id: 'grafico-3', type: 'chart', chart_type: 'area_apilada', row: 1, order: 4, width: 6, height: 420,
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

  it('una tabla multi-columna (Tabla 1) se renderiza en el grid', async () => {
    const TABLA_COMPONENTE = {
      component_id: 'tabla-1', type: 'chart', chart_type: 'tabla', row: 1, order: 5, width: 12, height: 380,
      is_visible: true,
      content: {
        titulo: 'Tabla 1', columnas: ['Producto', 'Ventas', '% del total'],
        filas: [['A', 100, 100]], total: ['Total', 100, 100],
      },
      styles: {}, config: {},
    }
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [TABLA_COMPONENTE] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Tabla 1')).toBeInTheDocument()
    expect(screen.getByText('% del total')).toBeInTheDocument()
  })

  it('un componente de la Zona Personal (config.zona=personal) se renderiza en el grid, fuera del modo edición', async () => {
    const KPI_PERSONAL = {
      component_id: 'mi-kpi', type: 'kpi', chart_type: '', row: 1, order: 20, width: 6, height: 180,
      is_visible: true, content: { titulo: 'Mi KPI personal', valor: 42 }, styles: {}, config: { zona: 'personal' },
    }
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [KPI_COMPONENTE, KPI_PERSONAL] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(screen.getByText('Mi KPI personal')).toBeInTheDocument()
    // Fuera de modo edición no hay ningún recuadro/rótulo de zona — solo aparece en el editor.
    expect(screen.queryByText('Zona personal')).not.toBeInTheDocument()
  })

  describe('panel de paleta de componentes (Zona Personal)', () => {
    it('fuera de modo edición, el panel de paleta no aparece', async () => {
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ modoEdicion: false }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      expect(screen.queryByText('Componentes')).not.toBeInTheDocument()
    })

    it('en modo edición, el panel de paleta se abre solo (sin acción adicional del usuario)', async () => {
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ modoEdicion: true }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      expect(await screen.findByText('Componentes')).toBeInTheDocument()
      expect(screen.getByText('Separador')).toBeInTheDocument()
      expect(screen.getByText('Título')).toBeInTheDocument()
      expect(screen.getByText('Tarjeta KPI')).toBeInTheDocument()
      expect(screen.getByText('Gráfico')).toBeInTheDocument()
      expect(screen.getByText('Tabla')).toBeInTheDocument()
    })

    it('clic en "Separador" (sin cambios sin guardar) lo agrega de inmediato y recarga', async () => {
      const recargar = vi.fn()
      dashboardLayoutService.agregarComponentePresentacional.mockResolvedValue({})
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ modoEdicion: true, hayCambiosSinGuardar: () => false, recargar }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      await userEvent.click(await screen.findByText('Separador'))

      await waitFor(() => expect(dashboardLayoutService.agregarComponentePresentacional).toHaveBeenCalledWith(
        'finanzas', { tipo: 'text', zona: 'personal' },
      ))
      await waitFor(() => expect(recargar).toHaveBeenCalled())
      expect(screen.queryByText('Agregar a la Zona Personal')).not.toBeInTheDocument()
    })

    it('clic en "Gráfico" abre el modal de configuración, preseleccionado en ese tipo', async () => {
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ modoEdicion: true, hayCambiosSinGuardar: () => false }))
      carteraService.obtenerArchivoActualDashboard.mockResolvedValue({ disponible: false })
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      await userEvent.click(await screen.findByText('Gráfico'))

      expect(await screen.findByText('Agregar a la Zona Personal')).toBeInTheDocument()
      expect(dashboardLayoutService.agregarComponentePresentacional).not.toHaveBeenCalled()
    })

    it('con cambios sin guardar, pide confirmación antes de agregar', async () => {
      dashboardLayoutService.agregarComponentePresentacional.mockResolvedValue({})
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ modoEdicion: true, hayCambiosSinGuardar: () => true }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      await userEvent.click(await screen.findByText('Título'))

      expect(dashboardLayoutService.agregarComponentePresentacional).not.toHaveBeenCalled()
      expect(screen.getByText(/se guarda de inmediato y actualiza el/)).toBeInTheDocument()

      await userEvent.click(screen.getByRole('button', { name: 'Continuar' }))
      await waitFor(() => expect(dashboardLayoutService.agregarComponentePresentacional).toHaveBeenCalledWith(
        'finanzas', { tipo: 'title', zona: 'personal' },
      ))
    })

    it('abrir "Configurar" de un componente existente oculta el panel de paleta', async () => {
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({
        modoEdicion: true, borrador: [KPI_COMPONENTE], seleccionado: 'kpi-1',
      }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      expect(screen.queryByText('Componentes')).not.toBeInTheDocument()
    })
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

  it('Tabla 3 vuelve a mostrar siempre su contenido normal (último archivo), nunca la comparativa histórica', async () => {
    const TABLA_3 = {
      component_id: 'tabla-3', type: 'chart', chart_type: 'tabla', row: 1, order: 11, width: 12, height: 380,
      is_visible: true,
      content: { titulo: 'Tabla 3', columnas: ['Producto', 'Ventas'], filas: [['A', 100]] },
      styles: {}, config: {},
      mapeo: { disponible: true, columna_id: 'Producto', columnas_valor: [{ columna: 'Ventas', tipo_agregacion: 'suma' }] },
    }
    useGenericDashboardBuilder.mockReturnValue(builderBase())
    useDashboardLayout.mockReturnValue(layoutBase({ borrador: [TABLA_3] }))
    renderPagina()
    await screen.findByRole('heading', { name: 'Finanzas' })

    expect(await screen.findByText('Tabla 3')).toBeInTheDocument()
    expect(screen.getAllByText('A').length).toBeGreaterThan(0)
    expect(screen.queryByText('Histórica')).not.toBeInTheDocument()
  })

  describe('Tabla 4 y Tabla 5 (comparación histórica en vivo)', () => {
    const TABLA_4 = {
      component_id: 'tabla-4', type: 'chart', chart_type: 'tabla', row: 1, order: 12, width: 6, height: 340,
      is_visible: true,
      content: { titulo: 'Tabla 4', columnas: ['Producto', 'Ventas'], filas: [['A', 100]] },
      styles: {}, config: {}, mapeo: {},
    }

    it('sin columnas históricas configuradas, muestra el contenido normal (con la etiqueta "Histórica") sin comparar', async () => {
      historicoService.listarCargasHistoricas.mockResolvedValue({
        cargas: [], columnas_disponibles: [], columnas_historicas_configuradas: [],
      })
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ borrador: [TABLA_4] }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      expect(await screen.findByText('Tabla 4')).toBeInTheDocument()
      expect(screen.getByText('Histórica')).toBeInTheDocument()
      expect(historicoService.calcularTablaHistorica).not.toHaveBeenCalled()
    })

    it('con columnas históricas configuradas pero sin cargas históricas, cae al contenido normal', async () => {
      historicoService.listarCargasHistoricas.mockResolvedValue({
        cargas: [], columnas_disponibles: [], columnas_historicas_configuradas: ['Ventas'],
      })
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ borrador: [TABLA_4] }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      expect(await screen.findByText('Tabla 4')).toBeInTheDocument()
      expect(screen.getAllByText('A').length).toBeGreaterThan(0)
      expect(historicoService.calcularTablaHistorica).not.toHaveBeenCalled()
    })

    it('con columnas históricas configuradas y cargas históricas, muestra la tabla comparativa (con la etiqueta "Histórica") en vez del contenido normal', async () => {
      historicoService.listarCargasHistoricas.mockResolvedValue({
        cargas: [{ carga_id: 'c1', nombre_original: 'enero.xlsx', fecha_carga: '2026-01-01T00:00:00', fecha_corte: null, total_filas: 5 }],
        columnas_disponibles: ['Ventas'],
        columnas_historicas_configuradas: ['Ventas'],
      })
      historicoService.calcularTablaHistorica.mockResolvedValue({
        columnas: ['Archivo', 'Usuario', 'Fecha de carga', 'Fecha de corte', 'Ventas'],
        filas: [['enero.xlsx', 'admin', '2026-01-01', '', 100]],
      })
      useGenericDashboardBuilder.mockReturnValue(builderBase())
      useDashboardLayout.mockReturnValue(layoutBase({ borrador: [TABLA_4] }))
      renderPagina()
      await screen.findByRole('heading', { name: 'Finanzas' })

      await waitFor(() => expect(screen.getAllByText('enero.xlsx').length).toBeGreaterThan(0))
      expect(historicoService.calcularTablaHistorica).toHaveBeenCalledWith(
        'finanzas', [{ columna: 'Ventas', tipo_agregacion: 'suma' }],
      )
      expect(screen.getByText('Histórica')).toBeInTheDocument()
      // No es el contenido normal (que solo tenía la fila "A"/100 de un único archivo).
      expect(screen.queryByText('A')).not.toBeInTheDocument()
    })
  })
})
