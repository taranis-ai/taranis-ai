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
        manualChunks: {
          vue: ['vue', 'vue-router'],
          vuetify: ['vuetify', 'vuetify/components', 'vuetify/directives'],
          materialdesignicons: ['@mdi/font/css/materialdesignicons.css']
          // assess: (id) =>
          //   id.includes('@/views/users/AssessView.vue') ||
          //   id.includes('@/views/nav/AssessNav.vue') ||
          //   id.includes('@/views/users/NewsItemView.vue') ||
          //   id.includes('@/views/users/StoryView.vue')
          // analyze: (id) =>
          //   id.includes('@/views/users/AnalyzeView.vue') ||
          //   id.includes('@/views/nav/AnalyzeNav.vue') ||
          //   id.includes('@/views/users/ReportView.vue'),
          // publish: (id) =>
          //   id.includes('@/views/users/PublishView.vue') ||
          //   id.includes('@/views/nav/PublishNav.vue') ||
          //   id.includes('@/views/users/ProductView.vue'),
          // assets: (id) =>
          //   id.includes('@/views/users/AssetsView.vue') ||
          //   id.includes('@/views/nav/AssetsNav.vue') ||
          //   id.includes('@/views/users/AssetView.vue') ||
          //   id.includes('@/views/users/AssetGroupView.vue'),
          // user: (id) =>
          //   id.includes('@/views/users/settings/') ||
          //   id.includes('@/views/nav/UserNav.vue'),
          // config: (id) =>
          //   id.includes('@/views/admin/') ||
          //   id.includes('@/views/nav/ConfigNav.vue')
        }
      }
    }
  }
})
