import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import PublicNavbar from '../components/public/PublicNavbar'
import { useTheme } from '../context/ThemeContext'
import { seccionesVisiblesOrdenadas } from '../config/landingContent'

vi.mock('../context/ThemeContext', () => ({ useTheme: vi.fn() }))

function renderNavbar() {
  return render(<MemoryRouter><PublicNavbar /></MemoryRouter>)
}

describe('PublicNavbar', () => {
  beforeEach(() => {
    useTheme.mockReturnValue({ theme: { site_name: 'Dashboard de Cartera', short_name: 'Cartera', logo_url: '' } })
  })

  it('renderiza un enlace por cada sección visible de la landing', () => {
    renderNavbar()
    seccionesVisiblesOrdenadas().forEach((seccion) => {
      expect(screen.getByRole('link', { name: seccion.menuLabel })).toHaveAttribute('href', `#${seccion.id}`)
    })
  })

  it('muestra el nombre corto institucional en la marca', () => {
    renderNavbar()
    expect(screen.getByText('Cartera')).toBeInTheDocument()
  })

  it('incluye un botón "Ingresar" que lleva a /login', () => {
    renderNavbar()
    expect(screen.getByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/login')
  })

  it('el botón de menú móvil alterna aria-expanded', async () => {
    renderNavbar()
    const boton = screen.getByRole('button', { name: /abrir menú/i })
    expect(boton).toHaveAttribute('aria-expanded', 'false')

    await userEvent.click(boton)
    expect(screen.getByRole('button', { name: /cerrar menú/i })).toHaveAttribute('aria-expanded', 'true')
  })
})
