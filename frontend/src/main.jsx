import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import './styles.css'
import Dashboard from './pages/Dashboard.jsx'
import Admin from './pages/Admin.jsx'
import Privacy from './pages/Privacy.jsx'

function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <span className="brand">Air Métropole</span>
        <nav>
          <NavLink to="/" end>Tableau de bord</NavLink>
          <NavLink to="/admin">Admin</NavLink>
          <NavLink to="/confidentialite">Confidentialité</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/confidentialite" element={<Privacy />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
