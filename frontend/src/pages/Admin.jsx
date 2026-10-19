import { useState } from 'react'
import { api, isLogged, LABELS } from '../api.js'

// Espace admin (US-008, US-018) : connexion, seuils, alertes, anomalies, modèle, logs
export default function Admin() {
  const [logged, setLogged] = useState(isLogged())
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [tab, setTab] = useState('thresholds')
  const [data, setData] = useState(null)

  const login = async (e) => {
    e.preventDefault()
    try { await api.login(form.username, form.password); setLogged(true); setError(''); open('thresholds') }
    catch (err) { setError(err.message) }
  }
  const open = async (name) => {
    setTab(name); setData(null)
    const loaders = { thresholds: api.admin.thresholds, alerts: api.admin.alerts, anomalies: api.admin.anomalies,
      model: api.admin.model, audit: api.admin.auditLogs, logs: api.admin.appLogs }
    try { setData(await loaders[name]()) } catch (err) { setError(err.message); setLogged(isLogged()) }
  }

  if (!logged) return (
    <form className="card login" onSubmit={login}>
      <h2>Connexion administrateur</h2>
      <input placeholder="Identifiant" autoComplete="username" value={form.username}
        onChange={(e) => setForm({ ...form, username: e.target.value })} />
      <input placeholder="Mot de passe" type="password" autoComplete="current-password" value={form.password}
        onChange={(e) => setForm({ ...form, password: e.target.value })} />
      <button type="submit">Se connecter</button>
      {error && <p className="error">{error}</p>}
    </form>
  )

  return (
    <div className="grid">
      <div className="tabs">
        {[['thresholds', 'Seuils'], ['alerts', 'Alertes'], ['anomalies', 'Anomalies'], ['model', 'Modèle IA'],
          ['audit', 'Journal de sécurité'], ['logs', 'Logs applicatifs']].map(([k, l]) => (
          <button key={k} className={tab === k ? 'chip on' : 'chip'} onClick={() => open(k)}>{l}</button>
        ))}
        <button className="chip" onClick={async () => { await api.admin.collectNow(); open(tab) }}>Collecter maintenant</button>
        <button className="chip" onClick={async () => { await api.admin.predictNow(); open('model') }}>Recalculer la prévision</button>
      </div>
      {error && <p className="error">{error}</p>}
      <section className="card">{data ? <Panel tab={tab} data={data} reload={() => open(tab)} /> : <p className="muted">Chargement…</p>}</section>
    </div>
  )
}

function Panel({ tab, data, reload }) {
  if (tab === 'thresholds') return (
    <table><thead><tr><th>Polluant</th><th>Seuil (µg/m³)</th><th /></tr></thead><tbody>
      {data.map((t) => <ThresholdRow key={t.pollutant} t={t} reload={reload} />)}
    </tbody></table>)
  if (tab === 'model') {
    const best = data.metrics?.[data.best_model]
    return (
      <div>
        <p>Modèle retenu : <strong>{data.best_model}</strong> — entraîné le {new Date(data.trained_at).toLocaleString('fr-FR')}</p>
        <table><thead><tr><th>Modèle</th><th>RMSE</th><th>MAPE %</th><th>Précision %</th><th>Bonne classe %</th></tr></thead><tbody>
          {Object.entries(data.metrics || {}).map(([k, m]) => (
            <tr key={k} className={k === data.best_model ? 'highlight' : ''}><td>{k}</td><td>{m.rmse}</td><td>{m.mape}</td><td>{m.precision}</td><td>{m.class_accuracy}</td></tr>))}
        </tbody></table>
        {best && <p className="muted">Critère client : précision &gt; 70 % → {best.precision > 70 ? 'atteint' : 'non atteint'}.</p>}
      </div>)
  }
  if (tab === 'logs') return <pre className="logs">{data.join('')}</pre>
  if (!data.length) return <p className="muted">Rien à afficher.</p>
  const cols = Object.keys(data[0])
  return (
    <div className="table-wrap"><table><thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead><tbody>
      {data.map((row, i) => <tr key={i}>{cols.map((c) => <td key={c}>{String(row[c] ?? '')}</td>)}</tr>)}
    </tbody></table></div>)
}

function ThresholdRow({ t, reload }) {
  const [v, setV] = useState(t.value)
  return (
    <tr><td>{LABELS[t.pollutant] || t.pollutant}</td>
      <td><input type="number" min="1" value={v} onChange={(e) => setV(e.target.value)} /></td>
      <td><button onClick={async () => { await api.admin.setThreshold(t.pollutant, Number(v)); reload() }}>Enregistrer</button></td></tr>)
}
