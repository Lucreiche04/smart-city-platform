import { useEffect, useState } from 'react'
import { Chart as ChartJS, LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend } from 'chart.js'
import { Line } from 'react-chartjs-2'
import { api } from '../api.js'

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend)

const LEVEL_COLORS = { fluide: '#2e9d5b', 'modéré': '#d6a700', dense: '#e8792b', 'saturé': '#d63b3b' }

// Données de mobilité : trafic actuel, lien trafic -> pollution (élus), conseil (citoyens)
export default function MobilityPanel() {
  const [data, setData] = useState(null)
  useEffect(() => {
    const load = () => api.mobility(48).then(setData).catch(() => setData(null))
    load()
    const t = setInterval(load, 60_000)
    return () => clearInterval(t)
  }, [])
  if (!data?.current) return null

  const { current, impact, tip, series } = data
  const no2 = impact?.no2
  return (
    <section className="card">
      <div className="card-head">
        <h2>Trafic et pollution</h2>
        <span className="pill" style={{ background: LEVEL_COLORS[current.level] }}>
          Trafic {current.level} · {current.traffic_index}/100
        </span>
      </div>
      <div className="mobility-grid">
        <div className="chart">
          <Line
            data={{
              datasets: [
                { label: 'Indice de trafic (0-100)', data: series.map((r) => ({ x: r.hour, y: r.traffic_index })),
                  yAxisID: 'y1', borderColor: '#8a5cf6', pointRadius: 0, borderWidth: 2 },
                { label: 'NO₂ (µg/m³)', data: series.filter((r) => r.no2 != null).map((r) => ({ x: r.hour, y: r.no2 })),
                  yAxisID: 'y', borderColor: '#e8792b', pointRadius: 0, borderWidth: 1.5, borderDash: [4, 3] },
              ],
            }}
            options={{
              maintainAspectRatio: false,
              interaction: { mode: 'index', intersect: false },
              scales: {
                x: { type: 'time', grid: { display: false } },
                y: { position: 'left', title: { display: true, text: 'NO₂ µg/m³' } },
                y1: { position: 'right', min: 0, max: 100, grid: { drawOnChartArea: false },
                  title: { display: true, text: 'Trafic' } },
              },
            }}
          />
        </div>
        <div className="mobility-facts">
          <p><strong>{current.transit_ridership.toLocaleString('fr-FR')}</strong> voyageurs/heure dans les transports</p>
          {no2 && (
            <p>
              Sur 30 jours, <strong>10 points de trafic en moins</strong> vont de pair avec
              <strong> {Math.abs(no2.per_10_points)} µg/m³ de NO₂ en moins</strong>
              <span className="muted"> (corrélation r = {no2.r})</span>.
            </p>
          )}
          {tip && <p className="tip">{tip}</p>}
        </div>
      </div>
      <p className="legend-note">Données de trafic simulées (aucune API temps réel gratuite) ; corrélation, pas causalité.</p>
    </section>
  )
}
