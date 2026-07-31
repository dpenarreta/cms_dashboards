import { useState } from 'react'
import { Alert, Button, Form } from 'react-bootstrap'
import { PERMISOS, usePermisos } from '../../hooks/usePermisos'
import ConfirmModal from './ConfirmModal'

export default function EditModeToolbar({
  modoEdicion, vistaPrevia, cargando, hayCambiosSinGuardar,
  onActivarEdicion, onGuardar, onCancelar, onAlternarVistaPrevia, onRestablecer,
}) {
  const permisos = usePermisos()
  const [nombreEditor, setNombreEditor] = useState('Anónimo')
  const [confirmando, setConfirmando] = useState(null) // 'cancelar' | 'restablecer' | null

  if (!permisos.tiene(PERMISOS.DASHBOARD_VIEW)) return null

  if (!modoEdicion) {
    if (!permisos.tiene(PERMISOS.DASHBOARD_EDIT)) return null
    return (
      <Button variant="outline-primary" size="sm" onClick={onActivarEdicion}>
        Editar dashboard
      </Button>
    )
  }

  const pedirCancelar = () => {
    if (hayCambiosSinGuardar()) setConfirmando('cancelar')
    else onCancelar()
  }

  return (
    <div className="d-flex flex-wrap align-items-center gap-2" role="toolbar" aria-label="Herramientas de edición del dashboard">
      <Form.Control
        size="sm"
        style={{ width: 160 }}
        placeholder="Tu nombre (auditoría)"
        value={nombreEditor}
        onChange={(e) => setNombreEditor(e.target.value)}
        aria-label="Nombre para el registro de auditoría"
      />
      <Button size="sm" variant="outline-secondary" onClick={onAlternarVistaPrevia}>
        {vistaPrevia ? 'Volver a editar' : 'Vista previa'}
      </Button>
      {permisos.tiene(PERMISOS.DASHBOARD_CONFIGURATION_RESET) && (
        <Button size="sm" variant="outline-danger" onClick={() => setConfirmando('restablecer')} disabled={cargando}>
          Restablecer diseño
        </Button>
      )}
      <Button size="sm" variant="outline-secondary" onClick={pedirCancelar} disabled={cargando}>
        Cancelar
      </Button>
      <Button size="sm" variant="primary" onClick={() => onGuardar(nombreEditor)} disabled={cargando}>
        Guardar cambios
      </Button>

      <ConfirmModal
        show={confirmando === 'cancelar'}
        title="Descartar cambios sin guardar"
        confirmLabel="Descartar cambios"
        onConfirm={() => { setConfirmando(null); onCancelar() }}
        onCancel={() => setConfirmando(null)}
      >
        Tienes cambios sin guardar. Al confirmar se restaurará la última configuración guardada.
      </ConfirmModal>

      <ConfirmModal
        show={confirmando === 'restablecer'}
        title="Restablecer visibilidad de componentes"
        confirmLabel="Restablecer"
        onConfirm={() => { setConfirmando(null); onRestablecer(nombreEditor) }}
        onCancel={() => setConfirmando(null)}
      >
        <Alert variant="warning" className="mb-0">
          Esta acción vuelve a mostrar cualquier componente que hayas ocultado, para todos los
          usuarios. No se puede deshacer (aunque queda registrada en el historial).
        </Alert>
      </ConfirmModal>
    </div>
  )
}
