import { createVuetify } from 'vuetify'
import 'vuetify/lib/styles/main.sass'
import { aliases, mdi } from 'vuetify/iconsets/mdi'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { VDataTable, VDataTableServer } from 'vuetify/labs/VDataTable'
import { VInfiniteScroll } from 'vuetify/labs/VInfiniteScroll'

const dark = {
  dark: true,
  colors: {
    primary: '#7468E8',
    secondary: '#34a5e8',
    accent: '#cfcde5',
    info: '#2196F3',
    error: '#FF5252',
    success: '#4CAF50',
    warning: '#FFC107',
    grey: '#C9C9C9',
    background: '#f3f3f3',
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
    'awake-green-color': '#5d9458',
    'awake-yellow-color': '#E9C645',
    'awake-red-color': '#b65f5f'
  }
}

const light = {
  dark: false,
  colors: {
    primary: '#7468E8',
    secondary: '#E9C645',
    accent: '#cfcde5',
    info: '#2196F3',
    error: '#ba3b3b',
    success: '#4CAF50',
    warning: '#FFC107',
    grey: '#C9C9C9',
    background: '#f3f3f3',
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
    'awake-green-color': '#5d9458',
    'awake-yellow-color': '#E9C645',
    'awake-red-color': '#b65f5f'
  }
}

const theme = {
  defaultTheme: 'light',
  themes: {
    dark,
    light
  }
}

export const vuetify = createVuetify({
  components: {
    ...components,
    VDataTable,
    VDataTableServer,
    VInfiniteScroll
  },
  directives,
  theme: theme,
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi
    }
  }
})
