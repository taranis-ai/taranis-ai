import '@mdi/font/css/materialdesignicons.css'
import { createApp } from 'vue'
import Assess from './Assess.vue'
import { ApiService } from '@/services/api_service'
import { i18n } from '@/i18n/i18n'
import { vuetify } from '@/plugins/vuetify'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import VueDOMPurifyHTML from 'vue-dompurify-html'
import VueDatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

import { useMainStore } from '@/stores/MainStore'
export const app = createApp(Assess)

export let apiService = null
async function initializeApp() {
  app.use(i18n)

  const pinia = createPinia()
  pinia.use(piniaPluginPersistedstate)
  app.component('VueDatePicker', VueDatePicker)
  app.use(pinia)
  app.use(vuetify)
  app.use(VueDOMPurifyHTML)
  const mainStore = useMainStore()
  await mainStore.updateFromLocalConfig()
  const { coreAPIURL } = mainStore

  console.debug('CoreAPI initialized ', coreAPIURL)

  apiService = new ApiService(coreAPIURL)
  app.provide('$coreAPIURL', coreAPIURL)
  app.mount('#app')
}

initializeApp().then(() => {
  console.debug('App initialized')
})
