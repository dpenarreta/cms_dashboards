import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
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
})
