import { LABELS } from '../api.js'

// US-004 + critère MVP "au moins 3 KPI de pollution"
export default function KpiCards({ kpis }) {
  if (!kpis.length) return <p className="muted">En attente des premières mesures…</p>
  return (
    <div className="kpis">
      {kpis.map((k) => (
        <div key={k.pollutant} className={`card kpi ${k.exceeded ? 'alert' : ''}`}>
          <span className="kpi-label">{LABELS[k.pollutant] || k.pollutant}</span>
          <span className="kpi-value">{k.value}<small> µg/m³</small></span>
          {k.threshold && (
            <span className="kpi-sub">
              seuil {k.threshold} {k.exceeded ? '— dépassé' : ''}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}
