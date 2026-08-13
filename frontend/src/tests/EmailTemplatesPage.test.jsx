import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import EmailTemplatesPage from '../pages/administration/settings/EmailTemplatesPage'
import * as emailTemplatesService from '../services/emailTemplatesService'
import { useAuth } from '../context/AuthContext'

vi.mock('../services/emailTemplatesService')
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))

const PLANTILLA = {
  key: 'password_reset',
  subject: 'Recuperación de contraseña | {{ site_name }}',
  html_body: '<p>Hola {{ nombre_usuario }}, tu enlace: {{ enlace }}</p>',
  updated_at: '2026-08-01T00:00:00Z',
  variables: [
    { name: 'nombre_usuario', description: 'Nombre del usuario.' },
    { name: 'enlace', description: 'Enlace único para restablecer la contraseña.' },
  ],
}

function renderPagina() {
  return render(<MemoryRouter><EmailTemplatesPage /></MemoryRouter>)
}

describe('EmailTemplatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    emailTemplatesService.get.mockResolvedValue(PLANTILLA)
    useAuth.mockReturnValue({ user: { permissions: ['configuracion.ver'] } })
  })

  it('carga y muestra el asunto y la lista de variables disponibles', async () => {
    renderPagina()
    expect(await screen.findByDisplayValue('Recuperación de contraseña | {{ site_name }}')).toBeInTheDocument()
    expect(screen.getByText('{{ nombre_usuario }}')).toBeInTheDocument()
    expect(screen.getByText('{{ enlace }}')).toBeInTheDocument()
  })

  it('la vista previa sustituye las variables por datos de ejemplo', async () => {
    renderPagina()
    await screen.findByDisplayValue('Recuperación de contraseña | {{ site_name }}')
    expect(screen.getByText(/Asunto: Recuperación de contraseña \| Dashboard de Cartera/)).toBeInTheDocument()

    // Quill también convierte a `&nbsp;` los espacios normales del texto circundante (no solo
    // los de adentro de `{{ }}`) — comportamiento esperado, no lo que este test quiere probar.
    const iframe = screen.getByTitle('Vista previa del correo')
    const srcdoc = iframe.getAttribute('srcdoc').replace(/&nbsp;/g, ' ')
    expect(srcdoc).toContain('tu enlace: https://tu-dominio.com/reset-password?token=ejemplo-de-token')
  })

  it('la vista previa sustituye variables aunque el editor haya convertido los espacios en &nbsp;', async () => {
    // Quill reescribe el HTML al guardar y suele convertir espacios normales en `&nbsp;`
    // (comportamiento normal de un contenteditable) — sobre todo justo alrededor de `{{`/`}}`.
    emailTemplatesService.get.mockResolvedValue({
      ...PLANTILLA, html_body: '<h1>{{&nbsp;site_name&nbsp;}}</h1>',
    })
    renderPagina()
    await screen.findByDisplayValue('Recuperación de contraseña | {{ site_name }}')

    const iframe = screen.getByTitle('Vista previa del correo')
    expect(iframe.getAttribute('srcdoc')).toBe('<h1>Dashboard de Cartera</h1>')
  })

  it('guardar cambios en el asunto llama al servicio con el nuevo valor', async () => {
    emailTemplatesService.update.mockResolvedValue({ ...PLANTILLA, subject: 'Nuevo asunto' })
    renderPagina()
    const campoAsunto = await screen.findByDisplayValue('Recuperación de contraseña | {{ site_name }}')

    await userEvent.clear(campoAsunto)
    await userEvent.type(campoAsunto, 'Nuevo asunto')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    // El cuerpo puede llegar con `&nbsp;` en vez de espacios normales — normalización propia de
    // Quill al montar el editor (equivalente visualmente, no algo que dependa del asunto que se
    // está probando acá), así que no se compara con igualdad estricta.
    await waitFor(() => expect(emailTemplatesService.update).toHaveBeenCalled())
    const [key, payload] = emailTemplatesService.update.mock.calls[0]
    expect(key).toBe('password_reset')
    expect(payload.subject).toBe('Nuevo asunto')
    expect(payload.htmlBody.replace(/&nbsp;/g, ' ')).toBe(PLANTILLA.html_body)
    expect(await screen.findByText('Plantilla de correo guardada.')).toBeInTheDocument()
  })

  it('si falla el guardado, muestra el mensaje de error del backend', async () => {
    emailTemplatesService.update.mockRejectedValue({ response: { data: { mensaje: 'No se pudo.' } } })
    renderPagina()
    await screen.findByDisplayValue('Recuperación de contraseña | {{ site_name }}')

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    expect(await screen.findByText('No se pudo.')).toBeInTheDocument()
  })

  it('restablecer pide confirmación antes de llamar al servicio', async () => {
    renderPagina()
    await screen.findByDisplayValue('Recuperación de contraseña | {{ site_name }}')

    await userEvent.click(screen.getByRole('button', { name: 'Restablecer al contenido por defecto' }))

    expect(await screen.findByText(/se perderán/i)).toBeInTheDocument()
    expect(emailTemplatesService.reset).not.toHaveBeenCalled()
  })

  it('confirmar el restablecimiento llama al servicio y refresca el contenido', async () => {
    emailTemplatesService.reset.mockResolvedValue({
      ...PLANTILLA, subject: 'Asunto por defecto | {{ site_name }}', html_body: '<p>Contenido por defecto</p>',
    })
    renderPagina()
    await screen.findByDisplayValue('Recuperación de contraseña | {{ site_name }}')

    await userEvent.click(screen.getByRole('button', { name: 'Restablecer al contenido por defecto' }))
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer' }))

    await waitFor(() => expect(emailTemplatesService.reset).toHaveBeenCalledWith('password_reset'))
    expect(await screen.findByText('Plantilla restablecida al contenido por defecto.')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Asunto por defecto | {{ site_name }}')).toBeInTheDocument()
  })

  it('si falla la carga inicial, muestra un mensaje de error', async () => {
    emailTemplatesService.get.mockRejectedValue(new Error('falló'))
    renderPagina()
    expect(await screen.findByText('No se pudo cargar la plantilla de correo.')).toBeInTheDocument()
  })
})
