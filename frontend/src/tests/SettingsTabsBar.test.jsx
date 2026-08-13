import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SettingsTabsBar from '../components/admin/SettingsTabsBar'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

function renderBarra(permissions, ruta = '/admin/settings') {
  useAuth.mockReturnValue({ user: { permissions } })
  return render(<MemoryRouter initialEntries={[ruta]}><SettingsTabsBar /></MemoryRouter>)
}

describe('SettingsTabsBar', () => {
  beforeEach(() => vi.clearAllMocks())

  it('con permiso, muestra las tres pestañas', () => {
    renderBarra(['configuracion.ver'])
    expect(screen.getByRole('link', { name: 'Configuración institucional' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Plantilla base de dashboards' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Plantilla de correo' })).toBeInTheDocument()
  })

  it('sin el permiso, no muestra nada', () => {
    const { container } = renderBarra([])
    expect(container).toBeEmptyDOMElement()
  })

  it('en /admin/settings, la pestaña institucional queda activa (coincidencia exacta, no por prefijo)', () => {
    renderBarra(['configuracion.ver'], '/admin/settings')
    expect(screen.getByRole('link', { name: 'Configuración institucional' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Plantilla base de dashboards' })).not.toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Plantilla de correo' })).not.toHaveClass('active')
  })

  it('en /admin/settings/plantilla-base, esa pestaña queda activa', () => {
    renderBarra(['configuracion.ver'], '/admin/settings/plantilla-base')
    expect(screen.getByRole('link', { name: 'Plantilla base de dashboards' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Configuración institucional' })).not.toHaveClass('active')
  })

  it('en /admin/settings/email-templates, esa pestaña queda activa', () => {
    renderBarra(['configuracion.ver'], '/admin/settings/email-templates')
    expect(screen.getByRole('link', { name: 'Plantilla de correo' })).toHaveClass('active')
    expect(screen.getByRole('link', { name: 'Configuración institucional' })).not.toHaveClass('active')
  })

  it('los enlaces apuntan a las rutas correctas', () => {
    renderBarra(['configuracion.ver'])
    expect(screen.getByRole('link', { name: 'Configuración institucional' })).toHaveAttribute('href', '/admin/settings')
    expect(screen.getByRole('link', { name: 'Plantilla base de dashboards' })).toHaveAttribute('href', '/admin/settings/plantilla-base')
    expect(screen.getByRole('link', { name: 'Plantilla de correo' })).toHaveAttribute('href', '/admin/settings/email-templates')
  })
})
