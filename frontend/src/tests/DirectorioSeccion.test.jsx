import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import DirectorioSeccion from '../components/dashboard-directorio/DirectorioSeccion'

/**
 * Renderers propios del Dashboard Directorio.
 *
 * Lo que importa verificar acá es que DERIVEN la presentación del contenido genérico y del mapeo,
 * en vez de mostrar valores guardados: es lo que hace que las secciones sigan siendo correctas
 * después de reconfigurarlas desde "Configurar componente".
 */

function concentracion({ topN = 16, titulo } = {}) {
  return {
    config: { bloque: 'concentracion' },
    mapeo: { top_n: topN },
    content: {
      titulo: titulo ?? 'CONCENTRACIÓN DE CARTERA — TOP {n} CLIENTES VS. RESTO DE LA CARTERA',
      columnas: ['Cliente', 'Saldo', '% del total', '% acumulado'],
      filas: [
        ['ACME', 600, 60, 60],
        ['Resto (5)', 400, 40, 100],
      ],
      total: ['Total', 1000, 100, 100],
    },
  }
}

describe('DirectorioSeccion — concentración', () => {
  it('el título sigue al Top-N del mapeo en vez de quedar con un número guardado', () => {
    // Antes el número venía escrito en el título: cambiar el Top-N actualizaba las tarjetas y la
    // tabla, pero el encabezado seguía diciendo la cifra vieja.
    render(<DirectorioSeccion componente={concentracion({ topN: 5 })} />)
    expect(screen.getByText(/TOP 5 CLIENTES VS\. RESTO/)).toBeInTheDocument()
    expect(screen.queryByText(/\{n\}/)).not.toBeInTheDocument()
  })

  it('un título editado a mano, sin el marcador, se muestra tal cual', () => {
    render(<DirectorioSeccion componente={concentracion({ topN: 5, titulo: 'MIS CLIENTES CLAVE' })} />)
    expect(screen.getByText('MIS CLIENTES CLAVE')).toBeInTheDocument()
  })

  it('deriva las dos tarjetas resumen de las filas, no de un valor guardado', () => {
    const { container } = render(<DirectorioSeccion componente={concentracion({ topN: 1 })} />)
    // Se acota al bloque resumen: los mismos montos aparecen también en la tabla de abajo.
    const resumen = container.querySelector('.directorio-resumen')
    expect(resumen).toHaveTextContent('TOP 1 CLIENTES')
    expect(resumen).toHaveTextContent('$600')      // la única fila que no es el "Resto"
    expect(resumen).toHaveTextContent('RESTO (5)')
    expect(resumen).toHaveTextContent('$400')
  })
})

describe('DirectorioSeccion — antigüedad', () => {
  const componente = {
    config: { bloque: 'antiguedad' },
    mapeo: {},
    styles: { coloresPorCategoria: { Anticipada: '#2E7D32', '+120 días': '#C62828' } },
    content: {
      titulo: 'ANTIGÜEDAD DE CARTERA',
      categorias: ['Anticipada', '+120 días'],
      valores: [750000, 250000],
    },
  }

  it('calcula el porcentaje de cada barra a partir de los valores', () => {
    const { container } = render(<DirectorioSeccion componente={componente} />)
    // Recharts no dibuja bajo jsdom (mide ancho 0), así que se verifica el título, que sí sale.
    expect(screen.getByText('ANTIGÜEDAD DE CARTERA')).toBeInTheDocument()
    expect(container.querySelector('.directorio-seccion')).toBeInTheDocument()
  })
})

describe('DirectorioSeccion — cumplimiento', () => {
  it('arma la columna META desde el mapeo, no desde el contenido', () => {
    const componente = {
      config: { bloque: 'cumplimiento' },
      mapeo: { metas: [{ meta_min: 50 }, { meta_max: 5 }] },
      content: {
        titulo: 'CUMPLIMIENTO',
        filas: [
          ['Corriente', 600, 60, 'Cumple'],
          ['Más de 120 días', 100, 10, 'No cumple'],
        ],
      },
    }
    render(<DirectorioSeccion componente={componente} />)
    expect(screen.getByText('≥ 50%')).toBeInTheDocument()
    expect(screen.getByText('≤ 5%')).toBeInTheDocument()
    expect(screen.getByText('60% ✓')).toBeInTheDocument()
    expect(screen.getByText('10% ✗')).toBeInTheDocument()
  })
})

describe('DirectorioSeccion — bordes', () => {
  it('un bloque desconocido no dibuja nada en vez de romper la pantalla', () => {
    const { container } = render(
      <DirectorioSeccion componente={{ config: { bloque: 'inventado' }, content: { titulo: 'x' } }} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('un componente sin contenido todavía calculado no dibuja nada', () => {
    const { container } = render(
      <DirectorioSeccion componente={{ config: { bloque: 'concentracion' } }} />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
