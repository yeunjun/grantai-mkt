import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/grantai-mkt/',
  server: {
    proxy: {
      '/upload':       { target: 'http://localhost:8000', changeOrigin: true },
      '/match':        { target: 'http://localhost:8000', changeOrigin: true },
      '/matches':      { target: 'http://localhost:8000', changeOrigin: true },
      '/generate':     { target: 'http://localhost:8000', changeOrigin: true },
      '/health':       { target: 'http://localhost:8000', changeOrigin: true },
      '/admin':        { target: 'http://localhost:8000', changeOrigin: true },
    }
  }
})
