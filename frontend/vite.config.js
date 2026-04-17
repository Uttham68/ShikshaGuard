import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      '^/(anomaly|auth|budget-estimate|dashboard|data|forecast|health|models|my-proposals|planning|proposal|proposals|risk-score|school|simulate|simulation|train)(/|$)': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  }
})
