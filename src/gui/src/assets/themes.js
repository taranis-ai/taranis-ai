/* COLOR THEMES TARANIS NG */

const defaultDark = Object.freeze({
  // default dark theme for all
  primary: '#4092dd',
  secondary: '#34a5e8',
  accent: '#82B1FF',
  info: '#2196F3',
  error: '#FF5252',
  success: '#4CAF50',
  warning: '#FFC107',
  'cx-app-header': '#444',
  'cx-toolbar-filter': '#363636',
  // 'cx-combo-gray': '#f2f2f2',
  'cx-user-menu': '#3a3a3a',
  'cx-drawer-bg': '#424242',
  // 'cx-drawer-text': '#fff',
  'cx-drawer-text-invert': '#fff',
  // 'cx-line': '#f00',
  'cx-favorites': '#ff9d48',
  'cx-filter': '#9f02ff'
})

const taranisDefault = Object.freeze({
  light: {
    primary: '#4092dd',
    secondary: '#34a5e8',
    accent: '#82B1FF',
    info: '#2196F3',
    error: '#FF5252',
    success: '#4CAF50',
    warning: '#FFC107',
    'cx-app-header': '#c7c7c7',
    'cx-toolbar-filter': '#ffffff',
    'cx-combo-gray': '#f2f2f2',
    'cx-user-menu': '#d9d9d9',
    'cx-drawer-bg': '#4092dd',
    'cx-drawer-text': '#fff',
    'cx-drawer-text-invert': '#000',
    'cx-line': '#fafafa',
    'cx-favorites': '#ff9d48',
    'cx-filter': '#9f02ff',
    'cx-wordlist': '#FFC107'
  },
  dark: defaultDark
})

const taranisUsersDefault = Object.freeze({
  light: {
    primary: '#4092dd',
    secondary: '#34a5e8',
    accent: '#82B1FF',
    info: '#2196F3',
    error: '#FF5252',
    success: '#4CAF50',
    warning: '#FFC107',
    'cx-app-header': '#c7c7c7',
    'cx-toolbar-filter': '#ffffff',
    'cx-combo-gray': '#f2f2f2',
    'cx-user-menu': '#d9d9d9'
  },
  dark: defaultDark
})

export default Object.freeze({
  taranisDefault,
  taranisUsersDefault
})
