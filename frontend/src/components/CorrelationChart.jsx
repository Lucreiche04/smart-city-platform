import { useEffect, useState } from 'react'
import { Chart as ChartJS, LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend } from 'chart.js'
import { Line } from 'react-chartjs-2'
import { api } from '../api.js'

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend)

// US-013 : pollution et météo sur le même graphique, deux axes Y
export default function CorrelationChart() {
  const [rows, setRows] = useState([])
  useEffect(() => { api.correlation(168).then(setRows).catch(() => setRows([])) }, [])
  if (!rows.length) return null
  return (
    <section className="card">
      <h2>Pollution et vent (7 jours)</h2>
      <p className="muted">Quand le vent forcit, les particules se dispersent et le PM2.5 baisse.</p>
      <div className="chart">
        <Line
          data={{
            datasets: [
              { label: 'PM2.5 (µg/m³)', data: rows.map((r) => ({ x: r.hour, y: r.pm25 })), yAxisID: 'y',
                borderColor: '#1f6feb', pointRadius: 0, borderWidth: 2 },
              { label: 'Vent (m/s)', data: rows.map((r) => ({ x: r.hour, y: r.wind_speed })), yAxisID: 'y1',
                borderColor: '#2e9d5b', pointRadius: 0, borderWidth: 1.5, borderDash: [4, 3] },
            ],
          }}
          options={{
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
              x: { type: 'time', grid: { display: false } },
              y: { position: 'left', title: { display: true, text: 'PM2.5 µg/m³' } },
              y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Vent m/s' } },
            },
          }}
        />
      </div>
    </section>
  )
}
