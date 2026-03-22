import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth':    { target: 'http://localhost:8001', changeOrigin: true, rewrite: p => p.replace(/^\/auth/, '') },
      '/bins':    { target: 'http://localhost:8002', changeOrigin: true, rewrite: p => p.replace(/^\/bins/, '') },
      '/fleet':   { target: 'http://localhost:8003', changeOrigin: true, rewrite: p => p.replace(/^\/fleet/, '') },
      '/command': { target: 'http://localhost:8007', changeOrigin: true, rewrite: p => p.replace(/^\/command/, '') },
    },
  },
})
