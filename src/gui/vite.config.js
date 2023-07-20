import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite'
import path from 'path'

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 8081
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  plugins: [vue(), VueI18nPlugin(), vuetify({ autoImport: true })],
  build: {
    sourcemap: true,
    rollupOptions: {
      // https://rollupjs.org/guide/en/#outputmanualchunks
      output: {
        manualChunks: {
          vue: ['vue', 'vue-router'],
          vuetify: ['vuetify', 'vuetify/components', 'vuetify/directives'],
          materialdesignicons: ['@mdi/font/css/materialdesignicons.css']
        }
      }
    }
  }
})
