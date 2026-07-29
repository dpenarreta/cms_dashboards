import { Button, ButtonGroup } from 'react-bootstrap'

/**
 * Alternativa accesible al arrastre (sección 21/22): siempre disponible, funciona con teclado y
 * en pantallas táctiles donde el drag and drop es incómodo.
 */
export default function MoveButtons({ onMover, deshabilitarArriba, deshabilitarAbajo }) {
  return (
    <ButtonGroup size="sm" aria-label="Mover componente">
      <Button
        variant="outline-secondary"
        onClick={() => onMover('inicio')}
        disabled={deshabilitarArriba}
        aria-label="Mover al inicio"
        title="Mover al inicio"
      >
        «
      </Button>
      <Button
        variant="outline-secondary"
        onClick={() => onMover('arriba')}
        disabled={deshabilitarArriba}
        aria-label="Mover arriba"
        title="Mover arriba"
      >
        ‹
      </Button>
      <Button
        variant="outline-secondary"
        onClick={() => onMover('abajo')}
        disabled={deshabilitarAbajo}
        aria-label="Mover abajo"
        title="Mover abajo"
      >
        ›
      </Button>
      <Button
        variant="outline-secondary"
        onClick={() => onMover('fin')}
        disabled={deshabilitarAbajo}
        aria-label="Mover al final"
        title="Mover al final"
      >
        »
      </Button>
    </ButtonGroup>
  )
}
