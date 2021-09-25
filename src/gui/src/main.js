import Vue from 'vue'
import Vuetify from 'vuetify/lib';
//import colors from 'vuetify/lib/util/colors'
import App from './App.vue'
import {router} from './router'
import {store} from '@/store/store'
import ApiService from "@/services/api_service";
import VueI18n from 'vue-i18n'
import messages from "@/i18n/messages";
import VeeValidate from 'vee-validate';
import Themes from './assets/themes';
import {Scroll} from 'vuetify/lib/directives';
import CKEditor from '@ckeditor/ckeditor5-vue'
import VueCookies from 'vue-cookies'
import VueSSE from 'vue-sse';
import DatetimePicker from 'vuetify-datetime-picker';
import CSButton from '../src/components/common/CSButton'

Vue.config.productionTip = false;

Vue.use(require('vue-cookies'))
Vue.use(VueCookies);
Vue.use(VueSSE)
Vue.use(DatetimePicker)

Vue.use(Vuetify, {
    directives: {
        Scroll
    }
});

Vue.use(CKEditor);

const vuetify = new Vuetify({

    theme: {
        dark: false,
        themes: Themes['taranisDefault']
    },
    icons: {
        iconfont: 'mdi',
    },
});

Vue.use(VueI18n);

const i18n = new VueI18n({
    locale: ((typeof(process.env.VUE_APP_TARANIS_NG_LOCALE) == "undefined") ? "$VUE_APP_TARANIS_NG_LOCALE" : process.env.VUE_APP_TARANIS_NG_LOCALE),
    fallbackLocale: 'en',
    messages
});

Vue.use(VeeValidate, {
    i18nRootKey: 'validations',
    i18n,
});

ApiService.init(((typeof(process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API));

if (localStorage.ACCESS_TOKEN) {
    store.dispatch('setToken', (localStorage.ACCESS_TOKEN)).then()
}

Vue.component('cs-button', CSButton);

export const vm = new Vue({
    i18n,
    vuetify,
    store,
    router,
    render: h => h(App),

}).$mount('#app');



