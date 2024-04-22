function getQueryStringFromObject(filterObject) {
  return Object.entries(filterObject)
    .filter(([, val]) => val != null)
    .map(([key, val]) => `${key}=${val}`)
    .join('&')
}

function encodeAmpersand(value) {
  return value.replace(/&/g, '%2526')
}

export function getQueryStringFromNestedObject(filterObject) {
  if (!filterObject) {
    return ''
  }
  return Object.entries(filterObject)
    .filter(([, val]) => val != null)
    .map(([key, val]) => {
      if (Array.isArray(val)) {
        return val.map((v) => `${key}=${encodeAmpersand(v)}`).join('&')
      }
      if (typeof val === 'object') {
        return getQueryStringFromObject(val)
      }
      return `${key}=${val}`
    })
    .join('&')
}
