import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

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
    port: 5173,
    open: false,
    host: '127.0.0.1'
  }
})
