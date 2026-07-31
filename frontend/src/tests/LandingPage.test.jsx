import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import LandingPage from '../pages/public/LandingPage'
import { useTheme } from '../context/ThemeContext'
import { HERO_CONTENT, LANDING_SECTIONS, seccionesDeContenido } from '../config/landingContent'

vi.mock('../context/ThemeContext', () => ({ useTheme: vi.fn() }))

function renderPagina() {
  return render(<MemoryRouter><LandingPage /></MemoryRouter>)
}

describe('LandingPage', () => {
  beforeEach(() => {
    useTheme.mockReturnValue({ theme: { site_name: 'Dashboard de Cartera', short_name: 'Cartera', logo_url: '' } })
  })

  it('renderiza el hero con su título y los dos llamados a la acción', () => {
    renderPagina()
    expect(screen.getByText(HERO_CONTENT.title)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: HERO_CONTENT.primaryCtaLabel })).toHaveAttribute('href', HERO_CONTENT.primaryCtaHref)
    expect(screen.getAllByRole('link', { name: HERO_CONTENT.secondaryCtaLabel })[0]).toHaveAttribute('href', '/login')
  })

  it('renderiza las secciones de contenido configuradas, cada una con su título', () => {
    renderPagina()
    seccionesDeContenido().forEach((seccion) => {
      expect(screen.getByRole('heading', { name: seccion.title })).toBeInTheDocument()
    })
  })

  it('renderiza las 10 áreas de ejemplo de la sección "Dashboards", sin exigir sesión', () => {
    renderPagina()
    const seccionDashboards = document.getElementById('dashboards')
    const dashboards = LANDING_SECTIONS.find((s) => s.id === 'dashboards')
    expect(dashboards.items).toHaveLength(10)
    dashboards.items.forEach((item) => {
      expect(within(seccionDashboards).getByText(item.title)).toBeInTheDocument()
    })
    // Ninguna tarjeta de esta sección es un enlace (no autentica, no navega a un dashboard real);
    // sí puede tener una etiqueta "Acceso restringido" (sección 6.5), que no es un enlace.
    expect(seccionDashboards.querySelectorAll('a')).toHaveLength(0)
    expect(within(seccionDashboards).getAllByText('Acceso restringido')).toHaveLength(10)
  })

  it('renderiza el diagrama de flujo de "Funcionamiento" con sus 5 pasos', () => {
    renderPagina()
    const seccionFuncionamiento = document.getElementById('funcionamiento')
    const funcionamiento = LANDING_SECTIONS.find((s) => s.id === 'funcionamiento')
    funcionamiento.steps.forEach((paso) => {
      expect(within(seccionFuncionamiento).getByText(paso.title)).toBeInTheDocument()
    })
  })

  it('el pie de página muestra el nombre institucional y el año actual', () => {
    renderPagina()
    const anioActual = new Date().getFullYear()
    expect(screen.getByText(new RegExp(`${anioActual}.*Dashboard de Cartera`))).toBeInTheDocument()
  })

  it('el pie de página incluye un enlace a /login', () => {
    renderPagina()
    const footer = document.querySelector('.landing-footer')
    expect(footer.querySelector('a[href="/login"]')).not.toBeNull()
  })
})
