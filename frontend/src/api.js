// Petit client HTTP : toutes les URLs sont relatives (/api/...) car Caddy sert
// le frontend et l'API sur le même domaine -> pas de problème CORS.
let token = null

export const setToken = (t) => { token = t }
export const isLogged = () => Boolean(token)

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`/api${path}`, { ...options, headers })
  if (res.status === 401) { token = null; throw new Error('Session expirée, reconnectez-vous') }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Erreur ${res.status}`)
  }
  return res.headers.get('content-type')?.includes('json') ? res.json() : res
}

export const api = {
  kpis: () => request('/kpis'),
  latest: () => request('/measurements/latest'),
  history: (pollutant, hours = 24) => request(`/measurements/history?pollutant=${pollutant}&hours=${hours}`),
  forecast: () => request('/forecast'),
  recommendations: () => request('/recommendations'),
  correlation: (hours = 168) => request(`/correlation?hours=${hours}`),
  mobility: (hours = 48) => request(`/mobility?hours=${hours}`),
  subscribe: (email) => request('/subscribers', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) }),
  unsubscribe: (email) => request(`/subscribers/${encodeURIComponent(email)}`, { method: 'DELETE' }),
  login: async (username, password) => {
    const body = new URLSearchParams({ username, password })
    const data = await request('/auth/login', { method: 'POST', body })
    setToken(data.access_token)
  },
  admin: {
    auditLogs: () => request('/admin/audit-logs'),
    appLogs: () => request('/admin/app-logs?lines=150'),
    thresholds: () => request('/admin/thresholds'),
    setThreshold: (pollutant, value) => request('/admin/thresholds', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pollutant, value }) }),
    alerts: () => request('/admin/alerts'),
    anomalies: () => request('/admin/anomalies'),
    model: () => request('/admin/model'),
    collectNow: () => request('/admin/collect-now', { method: 'POST' }),
    predictNow: () => request('/admin/predict-now', { method: 'POST' }),
  },
}

export const LABELS = { pm25: 'PM2.5', pm10: 'PM10', no2: 'NO₂', o3: 'O₃', so2: 'SO₂' }
