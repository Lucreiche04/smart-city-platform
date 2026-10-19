import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En dev (npm run dev), /api est redirigé vers le backend local
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
