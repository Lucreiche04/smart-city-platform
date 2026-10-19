// US-009 (prévision J+1) + US-011 (niveau de fiabilité) + explication pour la démo
export default function ForecastCard({ forecast }) {
  if (!forecast) return <section className="card"><h2>Demain</h2><p className="muted">Prévision en cours de calcul…</p></section>
  const rec = forecast.recommendation
  const m = forecast.explanation?.metrics
  return (
    <section className="card forecast" style={{ borderTopColor: rec.color }}>
      <h2>Prévision pour demain</h2>
      <p className="big">{forecast.value.toFixed(0)} <small>µg/m³ de PM2.5</small></p>
      <p>Niveau attendu : <strong style={{ color: rec.color }}>{rec.level}</strong></p>
      <p className="muted">
        Fourchette probable : {forecast.lower_bound.toFixed(0)} – {forecast.upper_bound.toFixed(0)} µg/m³
      </p>
      <div className="reliability">
        <span>Fiabilité du modèle</span>
        <div className="bar"><div style={{ width: `${forecast.reliability}%` }} /></div>
        <span>{forecast.reliability.toFixed(0)} %</span>
      </div>
      <details>
        <summary>Comment est calculée cette prévision ?</summary>
        <p>
          Modèle {forecast.model === 'random_forest' ? 'Random Forest' : 'de régression linéaire'} entraîné sur
          l'historique de pollution des 7 derniers jours, la prévision météo (vent, température, humidité, pression),
          le jour de la semaine et la saison.
          {m && <> Sur {forecast.explanation.test_days} jours de test : erreur moyenne de {m.mape} %
            (RMSE {m.rmse} µg/m³), bonne catégorie de pollution dans {m.class_accuracy} % des cas.</>}
        </p>
      </details>
    </section>
  )
}
