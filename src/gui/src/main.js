import 'material-design-icons-iconfont/dist/material-design-icons.css'
import '@mdi/font/css/materialdesignicons.css'
import Vue from 'vue'
import App from './App.vue'
import { router } from './router'
import { store } from '@/store/store'
import ApiService from '@/services/api_service'
import VueI18n from 'vue-i18n'
import messages from '@/i18n/messages'
import VeeValidate from 'vee-validate'
import CKEditor from '@ckeditor/ckeditor5-vue2'
import VueCookies from 'vue-cookies'
import VueSSE from 'vue-sse'
import DatetimePicker from 'vuetify-datetime-picker'

import layout_config from './assets/layout_config'
import SmoothScrollbar from 'vue-smooth-scrollbar'
import VueCalendarHeatmap from 'vue-calendar-heatmap'
import vuetify from '@/plugins/vuetify'

const CSL = {
  install(Vue) {
    Vue.prototype.UI = layout_config
    this.UI = () => { }
  }
}
Vue.use(CSL)

Vue.config.productionTip = false

Vue.use(require('vue-cookies'))
Vue.use(VueCookies)
Vue.use(VueSSE)
Vue.use(DatetimePicker)
Vue.use(VueCalendarHeatmap)

Vue.use(CKEditor)

Vue.use(VueI18n)

const i18n = new VueI18n({
  locale: ((typeof (process.env.VUE_APP_TARANIS_NG_LOCALE) === 'undefined') ? '$VUE_APP_TARANIS_NG_LOCALE' : process.env.VUE_APP_TARANIS_NG_LOCALE),
  fallbackLocale: 'en',
  messages
})

Vue.use(VeeValidate, {
  i18nRootKey: 'validations',
  i18n
})

const coreAPIURL = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) === 'undefined') ? '$VUE_APP_TARANIS_NG_CORE_API' : process.env.VUE_APP_TARANIS_NG_CORE_API)

ApiService.init(coreAPIURL)

if (localStorage.ACCESS_TOKEN) {
  store.dispatch('setToken', (localStorage.ACCESS_TOKEN)).then()
}

Vue.use(SmoothScrollbar)

export const vm = new Vue({
  i18n,
  vuetify,
  store,
  router,
  render: h => h(App)

}).$mount('#app')
