import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ThemeProvider, useTheme } from '../context/ThemeContext'
import * as brandingService from '../services/brandingService'

vi.mock('../services/brandingService', () => ({
  getCurrent: vi.fn(),
}))

const TEMA = {
  site_name: 'Mi Institución', short_name: 'MI', logo_url: '', favicon_url: '',
  color_primary: '#123456', color_secondary: '#654321', color_background: '#f0f0f0',
  color_headings: '#111111', color_text: '#222222', color_links: '#0000ff',
  color_buttons: '#444444', color_menu: '#555555',
  color_success: '#198754', color_danger: '#dc3545', color_warning: '#ffc107',
  color_info: '#0dcaf0', color_button_text: '#ffffff',
  font_primary_css: "'Inter', sans-serif", font_secondary_css: "'Inter', sans-serif",
  font_size_base: '18px', border_radius_css: '4px',
}

function Sonda() {
  const { theme } = useTheme()
  return <div data-testid="estado">{theme ? theme.site_name : 'SIN_TEMA'}</div>
}

describe('ThemeContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.documentElement.removeAttribute('style')
    document.title = ''
    document.getElementById('theme-bootstrap-overrides')?.remove()
  })

  it('aplica las variables CSS del tema recibido del backend', async () => {
    brandingService.getCurrent.mockResolvedValue(TEMA)
    render(<ThemeProvider><Sonda /></ThemeProvider>)

    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('Mi Institución'))
    expect(document.documentElement.style.getPropertyValue('--color-primary')).toBe('#123456')
    expect(document.documentElement.style.getPropertyValue('--border-radius')).toBe('4px')
    expect(document.title).toBe('Mi Institución')
  })

  it('publica los canales del color primario, para poder usarlo con transparencia sin color-mix()', async () => {
    // `.directorio-hallazgos` necesita el primario al 7%. Con `color-mix(in srgb, …)` Chrome
    // computa `color(srgb …)` y html2canvas ("Imprimir como PDF") corta la captura entera con
    // "unsupported color function". Con los canales sueltos, `rgba(var(--color-primary-rgb), .07)`
    // da el mismo resultado y se captura sin problema.
    brandingService.getCurrent.mockResolvedValue(TEMA)
    render(<ThemeProvider><Sonda /></ThemeProvider>)

    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('Mi Institución'))
    expect(document.documentElement.style.getPropertyValue('--color-primary-rgb')).toBe('18, 52, 86')
  })

  it('inyecta una hoja de estilos que reteñe los componentes reales de Bootstrap (Módulo B)', async () => {
    // Bootstrap 5.3 precompilado fija el color de `.btn-primary` como variable interna propia
    // (`--bs-btn-bg`), no como `var(--bs-primary)` — por eso la integración no puede limitarse a
    // sobreescribir variables en `:root`; tiene que inyectar reglas que redefinan esas variables
    // internas sobre la clase real que usan los botones/badges/enlaces de la aplicación.
    brandingService.getCurrent.mockResolvedValue(TEMA)
    render(<ThemeProvider><Sonda /></ThemeProvider>)

    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('Mi Institución'))
    const css = document.getElementById('theme-bootstrap-overrides').textContent

    expect(css).toMatch(/\.btn-primary\s*\{[^}]*--bs-btn-bg:\s*#123456/)
    expect(css).toMatch(/\.btn-outline-danger\s*\{[^}]*--bs-btn-color:\s*#dc3545/)
    expect(css).toMatch(/\.bg-success\s*\{\s*background-color:\s*#198754\s*!important/)
    expect(css).toMatch(/\.text-warning\s*\{\s*color:\s*#ffc107\s*!important/)
    expect(css).toMatch(/a, \.btn-link \{\s*color:\s*#0000ff/)
    // Oscurecido ~20% de #0000ff: cada canal se multiplica por 0.8 (0 -> 0, 255 -> 204 = 0xcc).
    expect(css).toMatch(/a:hover, \.btn-link:hover \{\s*color:\s*#0000cc/)
  })

  it('reteñe .alert-* (react-bootstrap <Alert variant>, usado en toda la app) y el foco/checked de formularios', async () => {
    // `.alert-danger` tampoco lee `--bs-danger`: fija `--bs-alert-bg`/`--bs-alert-color` desde
    // colores "subtle/emphasis" resueltos por Sass — mismo problema que los botones.
    brandingService.getCurrent.mockResolvedValue(TEMA)
    render(<ThemeProvider><Sonda /></ThemeProvider>)

    await waitFor(() => expect(screen.getByTestId('estado')).toHaveTextContent('Mi Institución'))
    const css = document.getElementById('theme-bootstrap-overrides').textContent

    expect(css).toMatch(/\.alert-danger\s*\{[^}]*--bs-alert-bg:/)
    expect(css).toMatch(/\.form-check-input:checked\s*\{[^}]*background-color:\s*#123456/)
    expect(css).toMatch(/\.form-control:focus,[^{]*\{[^}]*border-color:\s*#123456/)
  })

  it('si falla la consulta, no rompe y deja el tema en null (se conservan los valores estáticos de dashboard.css)', async () => {
    brandingService.getCurrent.mockRejectedValue(new Error('red caída'))
    render(<ThemeProvider><Sonda /></ThemeProvider>)

    await waitFor(() => expect(brandingService.getCurrent).toHaveBeenCalled())
    expect(screen.getByTestId('estado')).toHaveTextContent('SIN_TEMA')
  })

  it('useTheme lanza un error si se usa fuera de ThemeProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    function Rota() { useTheme(); return null }
    expect(() => render(<Rota />)).toThrow('useTheme debe usarse dentro de <ThemeProvider>.')
    consoleError.mockRestore()
  })
})
