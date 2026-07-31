import { describe, expect, it } from 'vitest'
import { LANDING_SECTIONS, seccionesVisiblesOrdenadas } from '../config/landingContent'

describe('landingContent', () => {
  it('seccionesVisiblesOrdenadas devuelve solo las secciones visibles, ordenadas por "order"', () => {
    const secciones = seccionesVisiblesOrdenadas()
    expect(secciones.every((s) => s.isVisible)).toBe(true)
    const ordenes = secciones.map((s) => s.order)
    expect(ordenes).toEqual([...ordenes].sort((a, b) => a - b))
  })

  it('la sección "dashboards" trae 10 áreas de ejemplo, sin enlaces reales', () => {
    const dashboards = LANDING_SECTIONS.find((s) => s.id === 'dashboards')
    expect(dashboards.items).toHaveLength(10)
    dashboards.items.forEach((item) => {
      expect(item).not.toHaveProperty('href')
      expect(item).not.toHaveProperty('path')
    })
  })

  it('no oculta ninguna sección si se agrega isVisible:false (respeta la config)', () => {
    const original = LANDING_SECTIONS.find((s) => s.id === 'beneficios')
    const conOculta = [...LANDING_SECTIONS.filter((s) => s.id !== 'beneficios'), { ...original, isVisible: false }]
    const visibles = conOculta.filter((s) => s.isVisible)
    expect(visibles.find((s) => s.id === 'beneficios')).toBeUndefined()
  })
})
