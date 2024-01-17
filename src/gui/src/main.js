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

export const app = createApp(App)
app.use(i18n)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.component('VueDatePicker', VueDatePicker)
app.use(router)
app.use(pinia)
app.use(vuetify)
app.use(VueDOMPurifyHTML)

import { useMainStore } from './stores/MainStore'
const mainStore = useMainStore()
mainStore.updateFromLocalConfig()
const { coreAPIURL, sentryDSN } = mainStore

console.debug('CoreAPI initialized ', coreAPIURL, sentryDSN)
export const apiService = new ApiService(coreAPIURL)
app.provide('$coreAPIURL', coreAPIURL)

if (sentryDSN) {
  Sentry.init({
    app,
    dsn: sentryDSN,
    autoSessionTracking: true,
    integrations: [
      new Sentry.BrowserTracing({
        routingInstrumentation: Sentry.vueRouterInstrumentation(router)
      }),
      new Sentry.Replay()
    ],
    environment: import.meta.env.DEV ? 'development' : 'production',
    tracesSampleRate: 1.0
  })
}

app.mount('#app')
