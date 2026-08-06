import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useColorMode } from '../hooks/useColorMode'
import { useTheme } from '../context/ThemeContext'

vi.mock('../context/ThemeContext', () => ({ useTheme: vi.fn() }))

function limpiarDocumento() {
  document.documentElement.removeAttribute('data-theme')
  document.documentElement.removeAttribute('data-bs-theme')
  document.documentElement.style.removeProperty('--color-background')
}

beforeEach(() => {
  localStorage.clear()
  limpiarDocumento()
  useTheme.mockReturnValue({ theme: null })
})

describe('useColorMode', () => {
  it('sin preferencia guardada, arranca en modo claro', () => {
    const { result } = renderHook(() => useColorMode())
    expect(result.current.oscuro).toBe(false)
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('light')
  })

  it('con la preferencia ya guardada en localStorage, arranca en modo oscuro', () => {
    localStorage.setItem('tema-color-modo', '1')
    const { result } = renderHook(() => useColorMode())
    expect(result.current.oscuro).toBe(true)
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark')
  })

  it('alternar cambia data-theme/data-bs-theme y persiste la preferencia', () => {
    const { result } = renderHook(() => useColorMode())
    act(() => result.current.alternar())

    expect(result.current.oscuro).toBe(true)
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark')
    expect(localStorage.getItem('tema-color-modo')).toBe('1')
  })

  it('alternar dos veces vuelve al modo claro', () => {
    const { result } = renderHook(() => useColorMode())
    act(() => result.current.alternar())
    act(() => result.current.alternar())

    expect(result.current.oscuro).toBe(false)
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    expect(localStorage.getItem('tema-color-modo')).toBe('0')
  })

  it('en modo oscuro, sobreescribe --color-background en línea (gana sobre la identidad institucional)', () => {
    const { result } = renderHook(() => useColorMode())
    act(() => result.current.alternar())
    expect(document.documentElement.style.getPropertyValue('--color-background')).toBe('#10141b')
  })

  it('volver a modo claro quita el override en línea de --color-background', () => {
    const { result } = renderHook(() => useColorMode())
    act(() => result.current.alternar())
    act(() => result.current.alternar())
    expect(document.documentElement.style.getPropertyValue('--color-background')).toBe('')
  })

  it('cuando la identidad institucional (re)carga, reaplica el modo oscuro sobre --color-background', () => {
    let theme = null
    useTheme.mockImplementation(() => ({ theme }))
    const { result, rerender } = renderHook(() => useColorMode())
    act(() => result.current.alternar())
    expect(document.documentElement.style.getPropertyValue('--color-background')).toBe('#10141b')

    // Simula lo que hace `ThemeContext.jsx::aplicarTema` al terminar de cargar: sobreescribe
    // `--color-background` en línea con el color institucional (claro).
    document.documentElement.style.setProperty('--color-background', '#eeeeee')
    theme = { color_background: '#eeeeee' }
    rerender()

    expect(document.documentElement.style.getPropertyValue('--color-background')).toBe('#10141b')
  })
})
