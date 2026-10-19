import { useEffect, useState } from 'react'
import { api } from '../api.js'
import KpiCards from '../components/KpiCards.jsx'
import HistoryChart from '../components/HistoryChart.jsx'
import AirMap from '../components/AirMap.jsx'
import ForecastCard from '../components/ForecastCard.jsx'
import CorrelationChart from '../components/CorrelationChart.jsx'
import MobilityPanel from '../components/MobilityPanel.jsx'

const REFRESH_MS = 60_000   // rafraîchissement automatique toutes les minutes

export default function Dashboard() {
  const [kpis, setKpis] = useState([])
  const [latest, setLatest] = useState([])
  const [forecast, setForecast] = useState(null)
  const [rec, setRec] = useState(null)
  const [email, setEmail] = useState('')
  const [msg, setMsg] = useState('')

  const load = () => {
    // Les 4 appels partent en parallèle : le dashboard s'affiche en une seule passe réseau
    api.kpis().then(setKpis).catch(() => {})
    api.latest().then(setLatest).catch(() => {})
    api.forecast().then(setForecast).catch(() => {})
    api.recommendations().then(setRec).catch(() => {})
  }
  useEffect(() => { load(); const t = setInterval(load, REFRESH_MS); return () => clearInterval(t) }, [])

  const subscribe = async (e) => {
    e.preventDefault()
    try { await api.subscribe(email); setMsg('Abonnement enregistré.'); setEmail('') } catch (err) { setMsg(err.message) }
  }

  return (
    <div className="grid">
      {rec && (
        <div className="banner" style={{ background: rec.color }}>
          Qualité de l'air actuelle : <strong>{rec.level}</strong> — {rec.advice}
        </div>
      )}
      <KpiCards kpis={kpis} />
      <div className="two-cols">
        <HistoryChart />
        <ForecastCard forecast={forecast} />
      </div>
      <div className="two-cols">
        <AirMap latest={latest} />
        <CorrelationChart />
      </div>
      <MobilityPanel />
      <section className="card actions">
        <div>
          <h2>Rapport pour les élus</h2>
          <a className="button" href="/api/reports/weekly.pdf">Télécharger le rapport PDF de la semaine</a>
        </div>
        <form onSubmit={subscribe}>
          <h2>Être alerté par email</h2>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="votre@email.fr" aria-label="Email" />
          <label className="consent"><input type="checkbox" required /> J'accepte de recevoir les alertes pollution. Désinscription possible à tout moment.</label>
          <button type="submit">S'abonner</button>
          {msg && <p className="muted">{msg}</p>}
        </form>
      </section>
    </div>
  )
}
