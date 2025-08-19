import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import vueDevTools from 'vite-plugin-vue-devtools'
import { livestoreDevtoolsPlugin } from '@livestore/devtools-vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(), 
    tailwindcss(),
    vueDevTools(),
    livestoreDevtoolsPlugin({ schemaPath: './src/livestore/schema.ts' }),
  ],
  server: {
    fs: {
      allow: [
        // Allow serving files from workspace root to access shared node_modules
        '../..',
      ]
    }
  }
})
