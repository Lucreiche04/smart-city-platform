import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'

// US-012 : carte interactive, couleur = niveau de PM2.5 de chaque point de mesure
const color = (v) => (v == null ? '#999' : v <= 10 ? '#2e9d5b' : v <= 25 ? '#d6a700' : v <= 50 ? '#e8792b' : '#d63b3b')

export default function AirMap({ latest }) {
  const stations = {}
  latest.forEach((m) => {
    stations[m.code] ??= { ...m, values: {} }
    stations[m.code].values[m.pollutant] = m.value
  })
  return (
    <section className="card">
      <h2>Carte par zone</h2>
      <div className="map">
        <MapContainer center={[48.858, 2.35]} zoom={12} scrollWheelZoom={false} style={{ height: '100%' }}>
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {Object.values(stations).map((s) => (
            <CircleMarker key={s.code} center={[s.lat, s.lon]} radius={18}
              pathOptions={{ color: color(s.values.pm25), fillOpacity: 0.55 }}>
              <Popup>
                <strong>{s.name}</strong> ({s.zone})<br />
                PM2.5 : {s.values.pm25 ?? '–'} µg/m³<br />
                {s.values.temperature != null && <>Température : {s.values.temperature} °C<br /></>}
                {s.kind === 'iot' ? 'Capteur IoT' : 'Station officielle'}
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
      <p className="legend-note">Vert ≤ 10 · Jaune ≤ 25 · Orange ≤ 50 · Rouge &gt; 50 µg/m³ (PM2.5)</p>
    </section>
  )
}
