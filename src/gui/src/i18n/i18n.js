import { createI18n } from 'vue-i18n'
import { messages } from '@/i18n/messages'
import { datetimeFormats } from '@/i18n/datetimeformat'

export const i18n = createI18n({
  legacy: false,
  locale:
    typeof import.meta.env.VITE_TARANIS_NG_LOCALE === 'undefined'
      ? 'en-GB'
      : import.meta.env.VITE_TARANIS_NG_LOCALE,
  fallbackLocale: 'en-GB',
  messages,
  datetimeFormats
})
