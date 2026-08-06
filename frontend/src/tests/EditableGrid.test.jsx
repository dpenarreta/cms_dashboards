import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import EditableGrid from '../components/dashboard-editor/EditableGrid'

function componente(id, overrides = {}) {
  return {
    component_id: id, type: 'kpi', chart_type: '', row: 1, order: 1, width: 3, height: 180,
    is_visible: true, content: {}, styles: {}, config: {}, mapeo: {},
    ...overrides,
  }
}

function registroPara(componentes) {
  return Object.fromEntries(componentes.map((c) => [c.component_id, { render: () => <div>{c.component_id}</div> }]))
}

function renderGrid(componentes, overrides = {}) {
  const props = {
    componentes,
    registro: registroPara(componentes),
    modoEdicion: true,
    vistaPrevia: false,
    seleccionado: null,
    onSeleccionar: vi.fn(),
    onMover: vi.fn(),
    onOcultar: vi.fn(),
    onMostrar: vi.fn(),
    onEliminar: vi.fn(),
    onReordenar: vi.fn(),
    permiteEstilo: true,
    permiteEliminar: true,
    ...overrides,
  }
  return { props, ...render(<EditableGrid {...props} />) }
}

describe('EditableGrid — Zona Personal', () => {
  it('sin componentes con config.zona=personal, no aparece el recuadro "Zona personal"', () => {
    renderGrid([componente('kpi-1', { order: 1 })])
    expect(screen.queryByRole('list', { name: 'Zona personal' })).not.toBeInTheDocument()
  })

  it('con 1+ componentes personales, aparece un recuadro "Zona personal" al final', () => {
    renderGrid([
      componente('kpi-1', { order: 1 }),
      componente('mi-kpi', { order: 2, config: { zona: 'personal' } }),
    ])
    const zonaPersonal = screen.getByRole('list', { name: 'Zona personal' })
    expect(zonaPersonal).toBeInTheDocument()
    expect(zonaPersonal.textContent).toContain('mi-kpi')
    expect(zonaPersonal.textContent).not.toContain('kpi-1')
  })

  it('la Zona Personal aparece después de las zonas de la plantilla fija', () => {
    renderGrid([
      componente('mi-kpi', { order: 2, config: { zona: 'personal' } }),
      componente('kpi-1', { order: 1 }),
    ])
    const listas = screen.getAllByRole('list')
    const etiquetas = listas.map((l) => l.getAttribute('aria-label'))
    expect(etiquetas.indexOf('Zona personal')).toBeGreaterThan(etiquetas.indexOf('Zona de KPIs'))
  })

  it('un componente sin zona conocida y sin marca personal sigue cayendo en "Otros componentes", separado de la Zona Personal', () => {
    renderGrid([
      componente('suelto', { order: 1 }),
      componente('mi-kpi', { order: 2, config: { zona: 'personal' } }),
    ])
    const otros = screen.getByRole('list', { name: 'Otros componentes' })
    expect(otros.textContent).toContain('suelto')
    expect(otros.textContent).not.toContain('mi-kpi')
    expect(screen.getByRole('list', { name: 'Zona personal' }).textContent).toContain('mi-kpi')
  })

  it('en vista normal (fuera de edición), un componente personal se renderiza sin ningún recuadro "Zona personal"', () => {
    renderGrid(
      [componente('kpi-1', { order: 1 }), componente('mi-kpi', { order: 2, config: { zona: 'personal' } })],
      { modoEdicion: false },
    )
    expect(screen.queryByRole('list', { name: 'Zona personal' })).not.toBeInTheDocument()
    expect(screen.getByText('mi-kpi')).toBeInTheDocument()
  })
})
