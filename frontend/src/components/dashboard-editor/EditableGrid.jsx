import { DndContext, PointerSensor, KeyboardSensor, closestCenter, useSensor, useSensors } from '@dnd-kit/core'
import { SortableContext, rectSortingStrategy, sortableKeyboardCoordinates, arrayMove } from '@dnd-kit/sortable'
import ComponentWrapper from './ComponentWrapper'

/**
 * Un único contenedor flex-wrap: cada componente reserva `width/12` del ancho. No hay
 * coordenadas fila/columna que mantener a mano, así que nunca hay superposición ni huecos que
 * reorganizar (sección 9) — el propio `flex-wrap` acomoda todo automáticamente al reordenar,
 * ocultar o cambiar de ancho. En pantallas angostas cada tarjeta puede forzar 100% por CSS
 * (sección 21) sin tocar el modelo de datos.
 */
export default function EditableGrid({
  componentes, registro, modoEdicion, vistaPrevia, seleccionado,
  onSeleccionar, onMover, onOcultar, onMostrar, onReordenar, permiteEstilo,
}) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const ordenados = [...componentes].sort((a, b) => a.order - b.order)
  const visibles = ordenados.filter((c) => c.is_visible)
  const ids = ordenados.map((c) => c.component_id)

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const desde = ids.indexOf(active.id)
    const hasta = ids.indexOf(over.id)
    onReordenar(arrayMove(ids, desde, hasta))
  }

  if (!modoEdicion || vistaPrevia) {
    return (
      <div className="d-flex flex-wrap">
        {visibles.map((c) => {
          const definicion = registro[c.component_id]
          if (!definicion) return null
          const anchoPorcentaje = `${(c.width / 12) * 100}%`
          return (
            <div key={c.component_id} style={{ flex: `0 0 ${anchoPorcentaje}`, maxWidth: anchoPorcentaje, padding: 8, boxSizing: 'border-box' }}>
              {definicion.render(c)}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={ids} strategy={rectSortingStrategy}>
        <div className="d-flex flex-wrap" role="list" aria-label="Componentes del dashboard (editable)">
          {ordenados.map((c, i) => {
            const definicion = registro[c.component_id]
            if (!definicion) return null
            return (
              <ComponentWrapper
                key={c.component_id}
                componente={{ ...c, render: () => definicion.render(c) }}
                esPrimero={i === 0}
                esUltimo={i === ordenados.length - 1}
                seleccionado={seleccionado === c.component_id}
                onSeleccionar={onSeleccionar}
                onMover={onMover}
                onOcultar={onOcultar}
                onMostrar={onMostrar}
                permiteEstilo={permiteEstilo}
              />
            )
          })}
        </div>
      </SortableContext>
    </DndContext>
  )
}
