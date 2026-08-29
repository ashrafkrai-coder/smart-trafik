import { defineConfig } from 'vite'

export default defineConfig({
  root: '.',
  publicDir: false,
  build: {
    outDir: '../frontend-dist',
    emptyOutDir: true
  },
  server: {
    port: 5500,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/video-feed': 'http://127.0.0.1:8000'
    }
  }
})
