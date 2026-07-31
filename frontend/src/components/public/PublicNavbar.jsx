import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '../../context/ThemeContext'
import { seccionesVisiblesOrdenadas } from '../../config/landingContent'

const SECCIONES = seccionesVisiblesOrdenadas()

export default function PublicNavbar() {
  const { theme } = useTheme()
  const [abierto, setAbierto] = useState(false)
  const [seccionActiva, setSeccionActiva] = useState(SECCIONES[0]?.id)
  const observadorRef = useRef(null)

  useEffect(() => {
    observadorRef.current = new IntersectionObserver(
      (entradas) => {
        const visible = entradas
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible) setSeccionActiva(visible.target.id)
      },
      { rootMargin: '-40% 0px -50% 0px', threshold: [0, 0.25, 0.5, 0.75, 1] },
    )
    SECCIONES.forEach((s) => {
      const el = document.getElementById(s.id)
      if (el) observadorRef.current.observe(el)
    })
    return () => observadorRef.current?.disconnect()
  }, [])

  const irASeccion = (id) => (e) => {
    e.preventDefault()
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    setAbierto(false)
  }

  return (
    <nav className="landing-navbar" aria-label="Menú principal">
      <div className="landing-navbar__inner">
        <a href="#inicio" className="landing-navbar__brand" onClick={irASeccion('inicio')}>
          {theme?.logo_url && <img src={theme.logo_url} alt="" height={28} />}
          <span>{theme?.short_name || theme?.site_name || 'Dashboard de Cartera'}</span>
        </a>

        <button
          type="button"
          className="landing-navbar__toggle"
          aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'}
          aria-expanded={abierto}
          onClick={() => setAbierto((v) => !v)}
        >
          <span />
          <span />
          <span />
        </button>

        <div className={`landing-navbar__links ${abierto ? 'landing-navbar__links--abierto' : ''}`}>
          {SECCIONES.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className={`landing-navbar__link ${seccionActiva === s.id ? 'landing-navbar__link--activo' : ''}`}
              onClick={irASeccion(s.id)}
            >
              {s.menuLabel}
            </a>
          ))}
          <Link to="/login" className="btn btn-primary btn-sm landing-navbar__cta">Ingresar</Link>
        </div>
      </div>
    </nav>
  )
}
