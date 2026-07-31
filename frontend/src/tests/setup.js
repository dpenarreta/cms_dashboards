import '@testing-library/jest-dom/vitest'

// jsdom no implementa IntersectionObserver; PublicNavbar (landing pública) lo usa para resaltar
// la sección activa del menú al hacer scroll.
if (typeof window !== 'undefined' && !window.IntersectionObserver) {
  window.IntersectionObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

// jsdom no implementa scrollIntoView; PublicNavbar lo usa para el scroll suave a cada sección.
if (typeof Element !== 'undefined' && !Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}

// jsdom no implementa matchMedia; react-bootstrap (Offcanvas) lo usa para breakpoints.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}
