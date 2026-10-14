import { Link } from 'react-router-dom'
import { useTheme } from '../../context/ThemeContext'
import PublicNavbar from '../../components/public/PublicNavbar'
import { CTA_CONTENT, FOOTER_CONTENT, HERO_CONTENT, seccionesDeContenido } from '../../config/landingContent'
import { NOMBRE_SITIO_POR_DEFECTO, inicialesDeMarca } from '../../utils/marca'
import '../../styles/landing.css'

const SECCIONES = seccionesDeContenido()

function DashboardMockup({ compacto = false }) {
  // Mockup de dashboard en CSS/HTML puro — nunca imágenes de stock ni ilustraciones de terceros.
  return (
    <div className={`hero-mockup ${compacto ? 'hero-mockup--compacto' : ''}`} aria-hidden="true">
      <div className="hero-mockup__bar">
        <span /><span /><span />
      </div>
      <div className="hero-mockup__body">
        <div className="hero-mockup__kpis">
          <div className="hero-mockup__kpi" />
          <div className="hero-mockup__kpi" />
          <div className="hero-mockup__kpi" />
        </div>
        <div className="hero-mockup__row">
          <div className="hero-mockup__chart hero-mockup__chart--bars">
            <span /><span /><span /><span /><span />
          </div>
          <div className="hero-mockup__chart hero-mockup__chart--donut" />
        </div>
        {!compacto && (
          <div className="hero-mockup__table">
            <div /><div /><div /><div />
          </div>
        )}
      </div>
    </div>
  )
}

// Composición decorativa alrededor del mockup: íconos de Bootstrap Icons en nodos flotantes,
// construida en CSS propio (nada de arte de terceros).
const NODOS_ILUSTRACION = ['bi-cart3', 'bi-cloud-arrow-up', 'bi-wrench', 'bi-image', 'bi-file-earmark-text', 'bi-gear']

function HeroIllustration() {
  return (
    <div className="hero-illustration">
      {NODOS_ILUSTRACION.map((icono, indice) => (
        <span key={icono} className={`hero-illustration__node hero-illustration__node--${indice + 1}`} aria-hidden="true">
          <i className={`bi ${icono}`} />
        </span>
      ))}
      <DashboardMockup />
    </div>
  )
}

// `color` es un tono de la Matriz (info/ok/warn/bad/neutral, ver `landingContent.js`): fondo y
// trazo salen de `--mz-{tono}-bg`/`-fg`, con su versión de modo oscuro.
function IconoCirculo({ icon, color }) {
  return (
    <div className={`icon-circle icon-circle--${color || 'info'}`} aria-hidden="true">
      <i className={`bi ${icon}`} />
    </div>
  )
}

function TarjetaIconGrid({ item }) {
  return (
    <div className="icon-card">
      <IconoCirculo icon={item.icon} color={item.color} />
      <h3 className="icon-card__titulo">{item.title}</h3>
      <p className="icon-card__descripcion">{item.description}</p>
    </div>
  )
}

function TarjetaDashboard({ item }) {
  return (
    <div className="landing-card">
      {item.icon && <div className="landing-card__icono" aria-hidden="true"><i className={`bi ${item.icon}`} /></div>}
      <h3 className="landing-card__titulo">{item.title}</h3>
      <p className="landing-card__descripcion">{item.description}</p>
      {item.indicadores && (
        <ul className="landing-card__indicadores">
          {item.indicadores.map((indicador) => <li key={indicador}>{indicador}</li>)}
        </ul>
      )}
      {item.indicadores && (
        <span className="mz-pill mz-pill--neutral landing-card__restringido">
          <i className="bi bi-lock" aria-hidden="true" /> Acceso restringido
        </span>
      )}
    </div>
  )
}

function ItemChecklist({ item }) {
  return (
    <li className="checklist-item">
      <span className="checklist-item__icono" aria-hidden="true"><i className={`bi ${item.icon || 'bi-check2-circle'}`} /></span>
      <div>
        <h3 className="checklist-item__titulo">{item.title}</h3>
        <p className="checklist-item__descripcion">{item.description}</p>
      </div>
    </li>
  )
}

function DiagramaFuncionamiento({ pasos }) {
  return (
    <div className="landing-flow">
      {pasos.map((paso, indice) => (
        <div key={paso.title} className="landing-flow__nodo-wrapper">
          <div className="landing-flow__nodo">
            <span className="landing-flow__paso">{indice + 1}</span>
            <h3 className="landing-flow__titulo">{paso.title}</h3>
            <p className="landing-flow__descripcion">{paso.description}</p>
          </div>
          {indice < pasos.length - 1 && <div className="landing-flow__flecha" aria-hidden="true"><i className="bi bi-arrow-down" /></div>}
        </div>
      ))}
    </div>
  )
}

function Seccion({ seccion }) {
  // Cada tipo de sección tiene su propia presentación visual (grid de íconos, banda de
  // características, checklist, tarjetas de dashboard) — el contenido sigue viniendo de
  // `landingContent.js`, config-driven (sección 6.11).
  if (seccion.id === 'funcionamiento') {
    return (
      <section id={seccion.id} className="feature-band">
        <div className="feature-band__inner">
          <div className="feature-band__texto">
            <h2 className="feature-band__titulo">{seccion.title}</h2>
            {seccion.description && <p className="feature-band__descripcion">{seccion.description}</p>}
            <DiagramaFuncionamiento pasos={seccion.steps} />
          </div>
          <div className="feature-band__mockup">
            <DashboardMockup compacto />
          </div>
        </div>
      </section>
    )
  }

  if (seccion.id === 'seguridad') {
    return (
      <section id={seccion.id} className="landing-section">
        <div className="landing-section__inner">
          <h2 className="landing-section__titulo">{seccion.title}</h2>
          <ul className="checklist">
            {seccion.items.map((item) => <ItemChecklist key={item.title} item={item} />)}
          </ul>
        </div>
      </section>
    )
  }

  if (seccion.id === 'dashboards') {
    return (
      <section id={seccion.id} className="landing-section">
        <div className="landing-section__inner">
          <h2 className="landing-section__titulo">{seccion.title}</h2>
          {seccion.description && <p className="landing-section__descripcion">{seccion.description}</p>}
          <div className="landing-section__grid landing-section__grid--denso">
            {seccion.items.map((item) => <TarjetaDashboard key={item.title} item={item} />)}
          </div>
        </div>
      </section>
    )
  }

  // que-es-un-cms / plataforma / beneficios: grid de íconos de colores (estilo "what you'll get").
  return (
    <section id={seccion.id} className="landing-section">
      <div className="landing-section__inner">
        <h2 className="landing-section__titulo">{seccion.title}</h2>
        {seccion.description && <p className="landing-section__descripcion">{seccion.description}</p>}
        <div className="icon-grid">
          {seccion.items.map((item) => <TarjetaIconGrid key={item.title} item={item} />)}
        </div>
      </div>
    </section>
  )
}

export default function LandingPage() {
  const { theme } = useTheme()
  const anioActual = new Date().getFullYear()
  const nombreSitio = theme?.site_name || NOMBRE_SITIO_POR_DEFECTO

  return (
    <div className="landing-page">
      <PublicNavbar />

      <header id="inicio" className="landing-hero--oscuro">
        <div className="landing-hero">
          <div className="landing-hero__texto">
            <p className="landing-hero__eyebrow">{HERO_CONTENT.eyebrow}</p>
            <h1 className="landing-hero__titulo">{HERO_CONTENT.title}</h1>
            <p className="landing-hero__subtitulo-corto">{HERO_CONTENT.subtitle}</p>
            <p className="landing-hero__subtitulo">{HERO_CONTENT.description}</p>
            <div className="d-flex gap-2 flex-wrap">
              <a href={HERO_CONTENT.primaryCtaHref} className="btn btn-primary btn-lg">{HERO_CONTENT.primaryCtaLabel}</a>
              <Link to={HERO_CONTENT.secondaryCtaHref} className="btn btn-outline-light btn-lg">{HERO_CONTENT.secondaryCtaLabel}</Link>
            </div>
          </div>
          <div className="landing-hero__mockup">
            <HeroIllustration />
          </div>
        </div>
      </header>

      {SECCIONES.map((seccion) => <Seccion key={seccion.id} seccion={seccion} />)}

      <section className="landing-cta">
        <h2>{CTA_CONTENT.title}</h2>
        <p>{CTA_CONTENT.subtitle}</p>
        <Link to={CTA_CONTENT.ctaHref} className="btn btn-light btn-lg">
          {CTA_CONTENT.ctaLabel} <i className="bi bi-arrow-right" aria-hidden="true" />
        </Link>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer__inner">
          <div className="landing-footer__marca">
            <div className="landing-footer__marca-linea">
              {theme?.logo_url
                ? <img src={theme.logo_url} alt="" height={22} />
                : <span className="landing-glyph" aria-hidden="true">{inicialesDeMarca(theme, nombreSitio)}</span>}
              <span>{nombreSitio}</span>
            </div>
            <p className="landing-footer__descripcion">{FOOTER_CONTENT.description}</p>
          </div>

          <nav className="landing-footer__links" aria-label="Enlaces del pie de página">
            {SECCIONES.map((s) => <a key={s.id} href={`#${s.id}`}>{s.menuLabel}</a>)}
            <Link to="/login">Ingresar</Link>
          </nav>

          <nav className="landing-footer__links" aria-label="Enlaces legales">
            {FOOTER_CONTENT.legalLinks.map((enlace) => <a key={enlace.label} href={enlace.href}>{enlace.label}</a>)}
          </nav>

          <span className="landing-footer__copyright">© {anioActual} {nombreSitio}. Todos los derechos reservados.</span>
        </div>
      </footer>
    </div>
  )
}
