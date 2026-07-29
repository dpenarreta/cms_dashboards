export default function KpiCard({ label, value, sub, accentColor, onClick }) {
  const interactivo = Boolean(onClick)

  return (
    <div
      className="kpi-card"
      style={{
        ...(accentColor ? { borderLeft: `4px solid ${accentColor}` } : {}),
        ...(interactivo ? { cursor: 'pointer' } : {}),
      }}
      role={interactivo ? 'button' : undefined}
      tabIndex={interactivo ? 0 : undefined}
      onClick={onClick}
      onKeyDown={interactivo ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } } : undefined}
      title={interactivo ? 'Pulse para ver el detalle' : undefined}
    >
      <div className="kpi-card__label">{label}</div>
      <div className="kpi-card__value">{value}</div>
      {sub && <div className="kpi-card__sub">{sub}</div>}
    </div>
  )
}
