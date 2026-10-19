import { useEffect, useState } from 'react'
import {
  Chart as ChartJS, LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend, Filler,
} from 'chart.js'
import 'chartjs-adapter-date-fns'
import annotationFree from './thresholdLine.js'
import { Line } from 'react-chartjs-2'
import { api, LABELS } from '../api.js'

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend, Filler, annotationFree)

// US-005 (filtre par polluant) + US-006 (évolution 24 h)
export default function HistoryChart() {
  const [pollutant, setPollutant] = useState('pm25')
  const [hours, setHours] = useState(24)
  const [data, setData] = useState(null)

  useEffect(() => {
    api.history(pollutant, hours).then(setData).catch(() => setData(null))
  }, [pollutant, hours])

  return (
    <section className="card">
      <div className="card-head">
        <h2>Évolution</h2>
        <div className="filters">
          {['pm25', 'pm10', 'no2'].map((p) => (
            <button key={p} className={p === pollutant ? 'chip on' : 'chip'} onClick={() => setPollutant(p)}>
              {LABELS[p]}
            </button>
          ))}
          <select value={hours} onChange={(e) => setHours(Number(e.target.value))} aria-label="Période">
            <option value={24}>24 h</option>
            <option value={168}>7 jours</option>
          </select>
        </div>
      </div>
      {data?.points?.length ? (
        <div className="chart">
          <Line
            data={{
              datasets: [{
                label: `${LABELS[pollutant]} (µg/m³)`,
                data: data.points.map((p) => ({ x: p.hour, y: p.value })),
                borderColor: '#1f6feb', backgroundColor: 'rgba(31,111,235,.08)', fill: true,
                pointRadius: 0, tension: 0.25, borderWidth: 2,
              }],
            }}
            options={{
              maintainAspectRatio: false,
              interaction: { mode: 'index', intersect: false },
              scales: {
                x: { type: 'time', time: { tooltipFormat: 'dd/MM HH:mm' }, grid: { display: false } },
                y: { beginAtZero: true, title: { display: true, text: 'µg/m³' } },
              },
              plugins: { legend: { display: false }, thresholdLine: { value: data.threshold } },
            }}
          />
        </div>
      ) : <p className="muted">Pas de données sur cette période.</p>}
      {data?.threshold && <p className="legend-note">Ligne rouge pointillée : seuil d'alerte {data.threshold} µg/m³</p>}
    </section>
  )
}
