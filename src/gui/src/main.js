import '@mdi/font/css/materialdesignicons.css'
import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import ApiService from '@/services/api_service'
import DatePicker from 'vue-datepicker-next'
import { i18n } from '@/i18n/i18n'
import { vuetify } from '@/plugins/vuetify'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import 'vue-datepicker-next/index.css'

export const app = createApp(App)

app.use(DatePicker)

app.use(i18n)

const coreAPIURL =
  typeof import.meta.env.VITE_TARANIS_NG_CORE_API === 'undefined'
    ? '/api'
    : import.meta.env.VITE_TARANIS_NG_CORE_API

ApiService.init(coreAPIURL)
app.provide('$coreAPIURL', coreAPIURL)

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

app.use(router)
app.use(pinia)
app.use(vuetify)
app.mount('#app')
