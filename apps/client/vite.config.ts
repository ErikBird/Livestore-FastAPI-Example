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
    livestoreDevtoolsPlugin({ 
      schemaPath: './src/livestore/schema.ts',
      // Explicitly set the base URL for devtools
      baseUrl: 'http://localhost:5173'
    }),
  ],
  server: {
    host: true, // This is equivalent to '0.0.0.0' but may work better with plugins
    port: 5173,
    strictPort: true,
    fs: {
      allow: [
        // Allow serving files from workspace root to access shared node_modules
        '../..',
      ]
    }
  }
})
