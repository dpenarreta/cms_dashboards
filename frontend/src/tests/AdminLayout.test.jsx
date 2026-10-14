import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AdminLayout from '../components/admin/AdminLayout'

// `Button as={Link}` renderiza un <a role="button">, así que se consulta por el rol button.

// `AdminSidebar` no es lo que se prueba acá y arrastra sesión, menú y modo de color: se sustituye
// por un marcador para dejar el test enfocado en la barra superior del layout.
vi.mock('../components/admin/AdminSidebar', () => ({
  default: () => <div>barra-lateral</div>,
}))

function renderEnRuta(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route element={<AdminLayout />}>
          <Route path="/app/dashboards" element={<div>listado</div>} />
          <Route path="/app/dashboards/:id" element={<div>un-dashboard</div>} />
          <Route path="/admin/users" element={<div>usuarios</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminLayout', () => {
  it('no muestra "Volver a Dashboards" estando ya en el listado de dashboards', () => {
    // Antes se mostraba siempre, incluido en la pantalla a la que apunta: un botón sin destino
    // útil justo donde el usuario ya está.
    renderEnRuta('/app/dashboards')
    expect(screen.getByText('listado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Volver a Dashboards' })).not.toBeInTheDocument()
  })

  it('muestra "Volver a Dashboards" dentro de un dashboard concreto', () => {
    renderEnRuta('/app/dashboards/cartera')
    expect(screen.getByRole('button', { name: 'Volver a Dashboards' })).toHaveAttribute('href', '/app/dashboards')
  })

  it('muestra "Volver a Dashboards" en las pantallas de administración', () => {
    renderEnRuta('/admin/users')
    expect(screen.getByRole('button', { name: 'Volver a Dashboards' })).toHaveAttribute('href', '/app/dashboards')
  })

  it('el título de la barra superior nombra la sección', () => {
    renderEnRuta('/admin/users')
    expect(screen.getByRole('heading', { level: 1, name: 'Usuarios y roles' })).toBeInTheDocument()
  })

  describe('tema claro/oscuro (ícono en la barra superior, como en la Matriz)', () => {
    beforeEach(() => {
      localStorage.clear()
      document.documentElement.removeAttribute('data-theme')
      document.documentElement.removeAttribute('data-bs-theme')
    })

    it('es un botón de solo ícono en la barra superior', () => {
      renderEnRuta('/app/dashboards')
      const boton = screen.getByRole('button', { name: 'Tema oscuro' })
      expect(boton.closest('.mz-topbar')).not.toBeNull()
      expect(boton).toHaveTextContent('')
    })

    it('clic en el botón activa el tema oscuro para toda la página (data-theme/data-bs-theme) y lo persiste', async () => {
      renderEnRuta('/app/dashboards')
      await userEvent.click(screen.getByRole('button', { name: 'Tema oscuro' }))

      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
      expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark')
      expect(localStorage.getItem('tema-color-modo')).toBe('1')
      expect(screen.getByRole('button', { name: 'Tema claro' })).toBeInTheDocument()
    })

    it('con el tema oscuro ya guardado, arranca mostrando el botón para volver al claro', () => {
      localStorage.setItem('tema-color-modo', '1')
      renderEnRuta('/app/dashboards')
      expect(screen.getByRole('button', { name: 'Tema claro' })).toBeInTheDocument()
    })
  })
})
