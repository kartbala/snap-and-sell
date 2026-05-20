import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Default proxy points at the local FastAPI backend on :5001.
// Set VITE_API_TARGET=https://snap-and-sell.onrender.com to preview the
// dev frontend against the live prod catalog + photos.
const target = process.env.VITE_API_TARGET || 'http://localhost:5001'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target, changeOrigin: true, secure: true },
      '/photos': { target, changeOrigin: true, secure: true },
    },
  },
})
