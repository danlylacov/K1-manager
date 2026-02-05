import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/rag-api': {
        target: 'http://rag-api:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/rag-api/, '')
      }
    }
  },
  build: {
    outDir: 'dist'
  }
})

