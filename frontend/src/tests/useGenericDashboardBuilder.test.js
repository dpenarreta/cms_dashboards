import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useGenericDashboardBuilder } from '../hooks/useGenericDashboardBuilder'
import * as carteraService from '../services/carteraService'

vi.mock('../services/carteraService')

function archivoDePrueba() {
  return new File(['contenido'], 'datos.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
}

beforeEach(() => {
  vi.clearAllMocks()
  carteraService.validarArchivo.mockResolvedValue({
    carga_id: 'carga-1', nombre_archivo: 'datos.xlsx', tamano_bytes: 100, total_filas_detectadas: 10,
    hojas_disponibles: ['Hoja1'], hoja_seleccionada: 'Hoja1',
  })
  carteraService.analizarColumnas.mockResolvedValue({
    total_filas: 10,
    columnas: [
      { nombre: 'Saldo', tipo: 'numerico', apta_para_valor: true, apta_para_categoria: false, motivo_no_apta: '' },
      { nombre: 'Ciudad', tipo: 'categorico', apta_para_valor: false, apta_para_categoria: true, motivo_no_apta: '' },
    ],
  })
  carteraService.recomendarGraficas.mockResolvedValue({
    recomendaciones: [{ id: 'Saldo::total', tipo_grafica: 'kpi', columna_valor: 'Saldo', columna_categoria: null, categorias_unicas: null }],
  })
})

describe('useGenericDashboardBuilder', () => {
  it('subirYValidar analiza el archivo y pasa a la fase ALIAS con las columnas y alias por defecto', async () => {
    const { result } = renderHook(() => useGenericDashboardBuilder('finanzas'))

    await act(async () => { await result.current.subirYValidar(archivoDePrueba()) })

    expect(result.current.fase).toBe(result.current.FASE.ALIAS)
    expect(result.current.columnas).toHaveLength(2)
    expect(result.current.aliases).toEqual({ Saldo: 'Saldo', Ciudad: 'Ciudad' })
    // El checkmark se precarga con la sugerencia del análisis automático.
    expect(result.current.utilizables).toEqual({ Saldo: true, Ciudad: true })
  })

  it('confirmarAliases envía solo las columnas marcadas como utilizables y pasa a RECOMENDACIONES', async () => {
    const { result } = renderHook(() => useGenericDashboardBuilder('finanzas'))
    await act(async () => { await result.current.subirYValidar(archivoDePrueba()) })

    act(() => result.current.actualizarUtilizable('Ciudad', false))
    await act(async () => { await result.current.confirmarAliases() })

    expect(carteraService.recomendarGraficas).toHaveBeenCalledWith('carga-1', ['Saldo'])
    expect(result.current.fase).toBe(result.current.FASE.RECOMENDACIONES)
    expect(result.current.recomendaciones).toHaveLength(1)
  })

  describe('agregarGrafica', () => {
    it('envía la descripción compuesta a partir de la recomendación y los alias', async () => {
      carteraService.agregarGrafica.mockResolvedValue({})
      const { result } = renderHook(() => useGenericDashboardBuilder('finanzas'))
      await act(async () => { await result.current.subirYValidar(archivoDePrueba()) })
      await act(async () => { await result.current.confirmarAliases() })

      await act(async () => { await result.current.agregarGrafica(result.current.recomendaciones[0], 'kpi') })

      expect(carteraService.agregarGrafica).toHaveBeenCalledWith('carga-1', expect.objectContaining({
        descripcion: 'Suma de todos los valores de "Saldo".',
      }))
    })
  })

  describe('volverAAlias', () => {
    it('regresa a la fase ALIAS sin perder el archivo, los alias ni los checkmarks ya elegidos', async () => {
      const { result } = renderHook(() => useGenericDashboardBuilder('finanzas'))
      await act(async () => { await result.current.subirYValidar(archivoDePrueba()) })
      act(() => result.current.actualizarAlias('Ciudad', 'Zona'))
      act(() => result.current.actualizarUtilizable('Ciudad', false))
      await act(async () => { await result.current.confirmarAliases() })

      act(() => result.current.volverAAlias())

      expect(result.current.fase).toBe(result.current.FASE.ALIAS)
      expect(result.current.archivoInfo.cargaId).toBe('carga-1')
      expect(result.current.aliases).toEqual({ Saldo: 'Saldo', Ciudad: 'Zona' })
      expect(result.current.utilizables).toEqual({ Saldo: true, Ciudad: false })
    })

    it('no vuelve a llamar al servicio (no repite el análisis ni la carga)', async () => {
      const { result } = renderHook(() => useGenericDashboardBuilder('finanzas'))
      await act(async () => { await result.current.subirYValidar(archivoDePrueba()) })
      await act(async () => { await result.current.confirmarAliases() })

      act(() => result.current.volverAAlias())

      expect(carteraService.validarArchivo).toHaveBeenCalledTimes(1)
      expect(carteraService.analizarColumnas).toHaveBeenCalledTimes(1)
    })

    it('preserva las gráficas ya agregadas en esta sesión', async () => {
      carteraService.agregarGrafica.mockResolvedValue({})
      const { result } = renderHook(() => useGenericDashboardBuilder('finanzas'))
      await act(async () => { await result.current.subirYValidar(archivoDePrueba()) })
      await act(async () => { await result.current.confirmarAliases() })
      await act(async () => { await result.current.agregarGrafica(result.current.recomendaciones[0]) })

      act(() => result.current.volverAAlias())

      expect(result.current.agregadas.has('Saldo::total')).toBe(true)
    })
  })
})
