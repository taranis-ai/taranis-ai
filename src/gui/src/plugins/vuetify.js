import Vue from 'vue'
import Vuetify from 'vuetify'
import 'vuetify/dist/vuetify.min.css'
import { Scroll } from 'vuetify/lib/directives'
import awakePinSvg from '@/assets/icons/pin.vue'
import awakeSearchSvg from '@/assets/icons/search.vue'

Vue.use(Vuetify)

const theme = {
  primary: '#7468E8',
  secondary: '#34a5e8',
  accent: '#82B1FF',
  info: '#2196F3',
  error: '#FF5252',
  success: '#4CAF50',
  warning: '#FFC107',
  grey: '#C9C9C9',
  'cx-app-header': '#E6E6E6',
  'cx-toolbar-filter': '#ffffff',
  'cx-combo-gray': '#f2f2f2',
  'cx-user-menu': '#d9d9d9',
  'cx-drawer-bg': '#ffffff',
  'cx-drawer-text': '#000000',
  'cx-drawer-text-invert': '#000',
  'cx-line': '#fafafa',
  'cx-favorites': '#ff9d48',
  'cx-filter': '#9f02ff',
  'cx-wordlist': '#FFC107',
  'main-text-color': '#575757',
  'dark-grey': '#575757',
  'awake-green-color': '#77BB70',
  'awake-red-color': '#D18E8E'
}

const vuetify = new Vuetify(
  {
    directives: {
      Scroll
    },
    icons: {
      iconfont: 'mdi',
      values: {
        awakePin: {
          component: awakePinSvg
        },
        awakeSearch: {
          component: awakeSearchSvg
        }
      }
    },
    theme: {
      themes: {
        dark: theme,
        light: theme
      }
    }
  })

export default vuetify
