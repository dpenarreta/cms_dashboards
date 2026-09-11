import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/tests/setup.js',
    globals: true,
    // El default de Vitest (5 s por test) no alcanza en esta máquina cuando la suite completa
    // corre en paralelo: 9 archivos fallaban por timeout y pasaban al correrlos aislados, lo que
    // hacía imposible distinguir un fallo real de uno de carga. Los tests que montan el editor
    // visual o el asistente de carga hacen bastante trabajo de render.
    testTimeout: 20000,
    hookTimeout: 20000,
    // Montar jsdom es lo caro de esta suite: saturar los núcleos hacía que cada archivo tardara
    // más de lo que ahorraba el paralelismo. En Vitest 4 estas opciones son de nivel superior
    // (`poolOptions` se retiró).
    pool: 'threads',
    minWorkers: 1,
    maxWorkers: 4,
  },
})
