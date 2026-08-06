import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import SettingsPage from '../pages/administration/settings/SettingsPage'
import * as brandingService from '../services/brandingService'
import { useTheme } from '../context/ThemeContext'

vi.mock('../services/brandingService')
vi.mock('../context/ThemeContext', () => ({ useTheme: vi.fn() }))

const TEMA = {
  site_name: 'Dashboard de Cartera', short_name: 'Cartera', logo_url: '', favicon_url: '',
  color_primary: '#2a78d6', color_secondary: '#eb6834', color_background: '#eeeeee',
  color_headings: '#000000', color_text: '#000000', color_links: '#2a78d6',
  color_buttons: '#2a78d6', color_menu: '#ffffff',
  color_success: '#198754', color_danger: '#dc3545', color_warning: '#ffc107',
  color_info: '#0dcaf0', color_button_text: '#ffffff',
  font_primary: 'system', font_secondary: 'system', font_size_base: '16px', border_radius: 'medium',
}
const OPCIONES = {
  fonts: [{ slug: 'system', label: 'Sistema (por defecto)' }, { slug: 'inter', label: 'Inter' }],
  border_radii: [{ slug: 'small', label: 'Pequeño' }, { slug: 'medium', label: 'Mediano' }, { slug: 'large', label: 'Grande' }],
}

describe('SettingsPage', () => {
  const reloadTheme = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    useTheme.mockReturnValue({ theme: TEMA, reloadTheme })
  })

  it('precarga los valores institucionales actuales', async () => {
    brandingService.getAdmin.mockResolvedValue(TEMA)
    brandingService.options.mockResolvedValue(OPCIONES)
    render(<MemoryRouter><SettingsPage /></MemoryRouter>)

    expect(await screen.findByDisplayValue('Dashboard de Cartera')).toBeInTheDocument()
    expect(screen.getByLabelText('Color principal (selector visual)')).toHaveValue('#2a78d6')
  })

  it('al guardar, envía los cambios y refresca el tema global', async () => {
    brandingService.getAdmin.mockResolvedValue(TEMA)
    brandingService.options.mockResolvedValue(OPCIONES)
    brandingService.update.mockResolvedValue({ ...TEMA, site_name: 'Nuevo nombre' })
    render(<MemoryRouter><SettingsPage /></MemoryRouter>)

    const campoNombre = await screen.findByLabelText('Nombre del sitio')
    await userEvent.clear(campoNombre)
    await userEvent.type(campoNombre, 'Nuevo nombre')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() => expect(brandingService.update).toHaveBeenCalledWith(expect.objectContaining({ site_name: 'Nuevo nombre' })))
    expect(reloadTheme).toHaveBeenCalled()
    expect(await screen.findByText('Configuración institucional guardada.')).toBeInTheDocument()
  })

  it('restablecer pide confirmación y refresca el tema global', async () => {
    brandingService.getAdmin.mockResolvedValue(TEMA)
    brandingService.options.mockResolvedValue(OPCIONES)
    brandingService.reset.mockResolvedValue(TEMA)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<MemoryRouter><SettingsPage /></MemoryRouter>)

    await screen.findByDisplayValue('Dashboard de Cartera')
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer' }))

    expect(window.confirm).toHaveBeenCalled()
    await waitFor(() => expect(brandingService.reset).toHaveBeenCalled())
    expect(reloadTheme).toHaveBeenCalled()
  })

  it('si se cancela la confirmación, no restablece', async () => {
    brandingService.getAdmin.mockResolvedValue(TEMA)
    brandingService.options.mockResolvedValue(OPCIONES)
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<MemoryRouter><SettingsPage /></MemoryRouter>)

    await screen.findByDisplayValue('Dashboard de Cartera')
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer' }))

    expect(brandingService.reset).not.toHaveBeenCalled()
  })

  it('muestra los campos de colores semánticos precargados', async () => {
    brandingService.getAdmin.mockResolvedValue(TEMA)
    brandingService.options.mockResolvedValue(OPCIONES)
    render(<MemoryRouter><SettingsPage /></MemoryRouter>)

    expect(await screen.findByLabelText('Éxito (selector visual)')).toHaveValue('#198754')
    expect(screen.getByLabelText('Peligro (selector visual)')).toHaveValue('#dc3545')
  })

  it('advierte (sin bloquear) cuando un color no alcanza el contraste WCAG AA frente a su contraparte', async () => {
    brandingService.getAdmin.mockResolvedValue({ ...TEMA, color_warning: '#ffc107', color_button_text: '#ffffff' })
    brandingService.options.mockResolvedValue(OPCIONES)
    render(<MemoryRouter><SettingsPage /></MemoryRouter>)

    const avisos = await screen.findAllByText(/contraste bajo/i)
    expect(avisos.length).toBeGreaterThan(0)
    // No bloquea: el botón de guardar sigue habilitado.
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeEnabled()
  })

  it('no advierte cuando un color tiene buen contraste frente a su contraparte', async () => {
    brandingService.getAdmin.mockResolvedValue({ ...TEMA, color_buttons: '#000000', color_button_text: '#ffffff' })
    brandingService.options.mockResolvedValue(OPCIONES)
    render(<MemoryRouter><SettingsPage /></MemoryRouter>)

    const campoBotones = (await screen.findByLabelText('Botones (selector visual)')).closest('.mb-3')
    expect(within(campoBotones).queryByText(/contraste bajo/i)).not.toBeInTheDocument()
  })
})
