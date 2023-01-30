import Vue from 'vue'
import Vuetify from 'vuetify'
import { Scroll } from 'vuetify/lib/directives'

Vue.use(Vuetify)
const colors = {
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
  'dark-grey': '#575757',
  'awake-green-color': '#77BB70',
  'awake-yellow-color': '#E9C645',
  'awake-red-color': '#D18E8E'
}

const theme = {
  themes: {
    dark: colors,
    light: colors
  }
}

const breakpoint = {
  thresholds: {
    xs: 600,
    sm: 976,
    md: 1280,
    lg: 2200
  },
  scrollBarWidth: 16
}

const icons = {
  iconfont: 'mdi'
}

const directives = { Scroll }

// Set vuetify

const vuetify = new Vuetify(
  {
    directives: directives,
    breakpoint: breakpoint,
    icons: icons,
    theme: theme
  })

export default vuetify
