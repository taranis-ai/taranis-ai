// https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat

const defaultShort = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit'
}

const defaultLong = {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false
}

export const datetimeFormats = {
  en: {
    short: {
      year: 'numeric',
      month: 'long',
      day: '2-digit'
    },
    long: defaultLong
  },
  de: {
    short: defaultShort,
    long: defaultLong
  },
  sk: {
    short: defaultShort,
    long: defaultLong
  }
}
