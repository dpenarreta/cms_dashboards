import { useState } from 'react'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Button } from 'react-bootstrap'
import MoveButtons from './MoveButtons'

/**
 * Chrome de edición alrededor de cualquier componente del dashboard (sección 7): borde visual,
 * manija de arrastre (dnd-kit, con soporte de teclado), engranaje para abrir el panel de
 * propiedades, ocultar/mostrar, eliminar (con confirmación in-line, ya que a diferencia de
 * ocultar no es reversible) y los botones de mover como alternativa accesible al arrastre.
 */
export default function ComponentWrapper({
  componente, esPrimero, esUltimo, seleccionado,
  onSeleccionar, onMover, onOcultar, onMostrar, onEliminar, permiteEstilo, permiteEliminar, esSuperusuario,
  estructuraBloqueada = false,
}) {
  // Dos bloqueos distintos, mismo efecto visual. `config.bloqueado` marca componentes sembrados
  // como estructura fija de un dashboard puntual; `estructuraBloqueada` congela el dashboard
  // entero (`Dashboard.estructura_bloqueada`). Un superusuario ve los controles habilitados en
  // ambos casos: del primero está exento, y del segundo puede salir confirmando su contraseña al
  // guardar, así que deshabilitárselos acá le escondería una salida que sí tiene.
  //
  // La protección REAL está en el backend (`services/dashboard_layout.py::validar_componentes`);
  // esto es solo para no invitar a intentar algo que el servidor va a rechazar.
  const bloqueado = (Boolean(componente.config?.bloqueado) || estructuraBloqueada) && !esSuperusuario
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: componente.component_id, disabled: bloqueado,
  })
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false)

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : componente.is_visible ? 1 : 0.5,
  }

  const anchoPorcentaje = `${(componente.width / 12) * 100}%`

  return (
    // Mismo criterio que `EditableGrid`: el ancho va como variable CSS para que las media
    // queries puedan apilarlo en pantallas angostas.
    <div
      className="dashboard-grid__celda"
      data-ancho={componente.width}
      style={{ ...style, '--ancho-panel': anchoPorcentaje }}
      ref={setNodeRef}
    >
      <div
        className={`h-100 ${seleccionado ? 'border-primary' : 'border-secondary'}`}
        style={{ border: '2px dashed', borderRadius: 10, padding: 6 }}
        role="group"
        aria-label={`Componente ${componente.component_id}, editable`}
      >
        <div className="d-flex justify-content-between align-items-center mb-1 flex-wrap gap-1">
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            aria-label={`Arrastrar para reordenar ${componente.component_id}`}
            title={bloqueado ? 'Componente bloqueado: no se puede reordenar' : 'Arrastrar para reordenar'}
            disabled={bloqueado}
            {...attributes}
            {...listeners}
            style={{ cursor: bloqueado ? 'not-allowed' : 'grab' }}
          >
            ⠿
          </button>
          <MoveButtons
            onMover={(direccion) => onMover(componente.component_id, direccion)}
            deshabilitarArriba={esPrimero || bloqueado}
            deshabilitarAbajo={esUltimo || bloqueado}
          />
          <div className="d-flex gap-1">
            {permiteEstilo && (
              <Button
                size="sm"
                variant={seleccionado ? 'primary' : 'outline-secondary'}
                onClick={() => onSeleccionar(componente.component_id)}
                aria-label={`Configurar ${componente.component_id}`}
                title="Configurar (título, descripción, colores)"
              >
                ⚙
              </Button>
            )}
            {!bloqueado && (componente.is_visible ? (
              <Button size="sm" variant="outline-secondary" onClick={() => onOcultar(componente.component_id)} title="Ocultar">
                Ocultar
              </Button>
            ) : (
              <Button size="sm" variant="outline-primary" onClick={() => onMostrar(componente.component_id)} title="Mostrar">
                Mostrar
              </Button>
            ))}
            {permiteEliminar && !bloqueado && (
              confirmandoEliminar ? (
                <div className="d-flex gap-1 align-items-center">
                  <span className="text-danger" style={{ fontSize: '0.8rem' }}>¿Eliminar?</span>
                  <Button size="sm" variant="danger" onClick={() => onEliminar(componente.component_id)}>Sí</Button>
                  <Button size="sm" variant="outline-secondary" onClick={() => setConfirmandoEliminar(false)}>No</Button>
                </div>
              ) : (
                <Button size="sm" variant="outline-danger" onClick={() => setConfirmandoEliminar(true)} title="Eliminar (no se puede deshacer)">
                  Eliminar
                </Button>
              )
            )}
          </div>
        </div>

        {componente.is_visible ? (
          // Se desactivan las interacciones internas (clics de drill-down, botones propios del
          // gráfico) mientras se está organizando el layout, para que no interfieran con el
          // arrastre (sección 7). En "Vista previa" el chrome de edición desaparece y todo
          // vuelve a ser interactivo con normalidad.
          <div style={{ pointerEvents: 'none' }}>{componente.render()}</div>
        ) : (
          <div className="text-center text-secondary py-4">Componente oculto</div>
        )}
      </div>
    </div>
  )
}
