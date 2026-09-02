import { defineConfig } from 'vite'
import { copyFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = dirname(fileURLToPath(import.meta.url))

function copyPwaFiles() {
  return {
    name: 'copy-pwa-files',
    closeBundle() {
      const outputRoot = resolve(frontendRoot, '../frontend-dist')
      const iconRoot = resolve(outputRoot, 'icons')
      mkdirSync(iconRoot, { recursive: true })
      copyFileSync(resolve(frontendRoot, 'sw.js'), resolve(outputRoot, 'sw.js'))
      copyFileSync(resolve(frontendRoot, 'manifest.json'), resolve(outputRoot, 'manifest.json'))
      copyFileSync(resolve(frontendRoot, 'offline.html'), resolve(outputRoot, 'offline.html'))
      copyFileSync(resolve(frontendRoot, 'icons/icon-192.svg'), resolve(iconRoot, 'icon-192.svg'))
      copyFileSync(resolve(frontendRoot, 'icons/icon-512.svg'), resolve(iconRoot, 'icon-512.svg'))
    }
  }
}

export default defineConfig({
  root: '.',
  base: './',
  publicDir: false,
  plugins: [copyPwaFiles()],
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
