import '@mdi/font/css/materialdesignicons.css'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import { ApiService } from '@/services/api_service'
import { i18n } from '@/i18n/i18n'
import { vuetify } from '@/plugins/vuetify'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import VueDOMPurifyHTML from 'vue-dompurify-html'
import VueDatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

import * as Sentry from '@sentry/vue'
import { useMainStore } from '@/stores/MainStore'
export const app = createApp(App)

export let apiService = null
async function initializeApp() {
  app.use(i18n)

  const pinia = createPinia()
  pinia.use(piniaPluginPersistedstate)
  app.component('VueDatePicker', VueDatePicker)
  app.use(router)
  app.use(pinia)
  app.use(vuetify)
  app.use(VueDOMPurifyHTML)
  const mainStore = useMainStore()
  await mainStore.updateFromLocalConfig()
  const { coreAPIURL, sentryDSN } = mainStore

  console.debug('CoreAPI initialized ', coreAPIURL, sentryDSN)

  apiService = new ApiService(coreAPIURL)
  app.provide('$coreAPIURL', coreAPIURL)

  if (sentryDSN) {
    Sentry.init({
      app,
      dsn: sentryDSN,
      replaysOnErrorSampleRate: 1.0,
      autoSessionTracking: true,
      integrations: [
        Sentry.browserTracingIntegration({ router }),
        Sentry.replayIntegration()
      ],
      environment: import.meta.env.DEV ? 'development' : 'production',
      tracesSampleRate: 1.0
    })
  }

  app.mount('#app')
}

initializeApp().then(() => {
  console.debug('App initialized')
})
