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
    rollupOptions: {
      // https://rollupjs.org/guide/en/#outputmanualchunks
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            const match = id.match(/[\\/]node_modules[\\/](.*?)([\\/]|$)/)
            if (match) {
              const pkg = match[1]
              if (pkg === '@vue') {
                return 'vue'
              }
              if (
                pkg === 'vuetify' ||
                pkg === 'pinia' ||
                pkg === 'vue-i18n' ||
                pkg === 'vue-router'
              ) {
                return 'vue_packages'
              }
              if (pkg === '@mdi') {
                return 'mdi'
              }
              if (pkg === 'chart.js' || pkg === 'vue-chartjs') {
                return 'chart'
              }
              return 'vendor'
            }
          }

          if (id.includes('/views/admin/')) {
            return 'admin_views'
          }

          return 'app'
        }
      }
    }
  }
})
