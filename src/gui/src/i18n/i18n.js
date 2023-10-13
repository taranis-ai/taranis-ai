import { createI18n } from 'vue-i18n'
import { messages } from '@/i18n/messages'
import { datetimeFormats } from '@/i18n/datetimeformat'

export const i18n = createI18n({
  legacy: false,
  locale:
    typeof import.meta.env.VITE_TARANIS_LOCALE === 'undefined'
      ? 'en'
      : import.meta.env.VITE_TARANIS_LOCALE,
  fallbackLocale: 'en',
  messages,
  datetimeFormats
})
