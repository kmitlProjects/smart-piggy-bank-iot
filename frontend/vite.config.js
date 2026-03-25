import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const frontendPort = Number(process.env.FRONTEND_PORT || '5173')
const frontendHost = process.env.FRONTEND_HOST || '127.0.0.1'
const apiTarget = process.env.VITE_API_TARGET || 'http://127.0.0.1:5001'

export default defineConfig({
  plugins: [react()],
  root: process.cwd(),
  publicDir: 'public',
  define: {
    global: 'globalThis',
    'process.env': {},
  },
  resolve: {
    alias: {
      buffer: resolve(__dirname, 'node_modules/buffer'),
      process: resolve(__dirname, 'node_modules/process/browser.js'),
      events: resolve(__dirname, 'node_modules/events/events.js'),
      util: resolve(__dirname, 'node_modules/util/util.js'),
    },
  },
  server: {
    port: frontendPort,
    open: false,
    host: frontendHost,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  }
})
