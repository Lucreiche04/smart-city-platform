import { useState } from 'react'
import { api } from '../api.js'

// RGPD : information + droit à l'oubli
export default function Privacy() {
  const [email, setEmail] = useState('')
  const [msg, setMsg] = useState('')
  const remove = async (e) => {
    e.preventDefault()
    try { await api.unsubscribe(email); setMsg('Vos données ont été supprimées.') } catch (err) { setMsg(err.message) }
  }
  return (
    <div className="grid narrow">
      <section className="card">
        <h2>Vos données</h2>
        <p>La plateforme ne stocke aucune donnée personnelle, sauf votre adresse email si vous vous abonnez aux alertes.
          Elle n'est utilisée que pour vous prévenir d'un épisode de pollution et n'est jamais transmise à un tiers.</p>
        <p>Les capteurs sont localisés à l'échelle du quartier : aucune géolocalisation précise n'est collectée.
          Ce site n'utilise pas de cookies de mesure d'audience.</p>
        <p>Responsable du traitement : Direction de la Transition Écologique de la Métropole.</p>
      </section>
      <form className="card" onSubmit={remove}>
        <h2>Supprimer mes données (droit à l'oubli)</h2>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="votre@email.fr" />
        <button type="submit">Supprimer définitivement</button>
        {msg && <p className="muted">{msg}</p>}
      </form>
    </div>
  )
}
