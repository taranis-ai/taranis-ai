import { useMainStore } from '@/stores/MainStore'
import { useFilterStore } from '@/stores/FilterStore'

export function xorConcat(array, element) {
  const i = array.indexOf(element)
  if (i === -1) {
    array.push(element)
  } else {
    array.splice(i, 1)
  }
  return array
}

export function getCleanHostname(url) {
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch (error) {
    return url
  }
}

export function notifySuccess(text) {
  const store = useMainStore()
  store.notification = {
    type: 'success',
    message: text,
    show: true
  }
}

export function notifyFailure(text) {
  const store = useMainStore()
  store.notification = {
    type: 'red',
    message: text,
    show: true
  }
}

export function emptyValues(obj) {
  const result = {}
  for (const key of Object.keys(obj)) {
    const value = obj[key]
    if (typeof value === 'string') {
      result[key] = ''
    } else if (Array.isArray(value)) {
      result[key] = []
    } else if (typeof value === 'object') {
      result[key] = emptyValues(value)
    } else {
      result[key] = undefined
    }
  }
  return result
}

export function objectFromFormat(format) {
  const newObject = {}
  format.map(function (item) {
    if (item === undefined || item.disabled) {
      return
    }
    if (item.type === 'switch') {
      newObject[item.name] = false
    } else if (
      item.type === 'text' ||
      item.type === 'textarea' ||
      item.type === 'select'
    ) {
      newObject[item.name] = ''
    } else if (item.type === 'number') {
      newObject[item.name] = 0
    } else if (item.type === 'table' || item.type === 'checkbox') {
      newObject[item.name] = []
    }
  })
  return flattenFormData(newObject, format)
}

export function flattenFormData(data, format) {
  const flattened = {}
  format.forEach((item) => {
    const key = item.parent ? `${item.parent}.${item.name}` : item.name
    if (item.parent) {
      if (!data[item.parent]) {
        data[item.parent] = {}
      }
      flattened[key] = data[item.parent][item.name]
    } else {
      flattened[key] = data[item.name]
    }
  })
  return flattened
}

// Reconstruct the data based on format
export function reconstructFormData(flattened, format) {
  const data = {}
  format.forEach((item) => {
    if (item.parent) {
      data[item.parent] = data[item.parent] || {}
      data[item.parent][item.name] = flattened[`${item.parent}.${item.name}`]
    } else {
      data[item.name] = flattened[item.name]
    }
  })
  return data
}

export function flattenObject(obj, parent) {
  let result = []
  let flat_obj = {}
  for (const key in obj) {
    if (typeof obj[key] === 'object') {
      result = result.concat(flattenObject(obj[key], key))
    } else {
      flat_obj = {
        name: key,
        type: typeof obj[key] === 'number' ? 'number' : 'text',
        label: key
      }
      if (parent) {
        flat_obj.parent = parent
      }
      if (key === 'id') {
        flat_obj.disabled = true
        result.unshift(flat_obj)
        continue
      }
      result.push(flat_obj)
    }
  }
  return result
}

export function tagIconFromType(tag_type) {
  if (tag_type === 'ORG' || tag_type === 'CVE_VENDOR') {
    return 'mdi-domain'
  }
  if (
    tag_type === 'LOC' ||
    tag_type === 'Country' ||
    tag_type === 'Municipality'
  ) {
    return 'mdi-map-marker-outline'
  }
  if (tag_type === 'CVE' || tag_type === 'CVE_PRODUCT') {
    return 'mdi-bookmark-outline'
  }
  if (tag_type === 'PER') {
    return 'mdi-account-outline'
  }
  if (tag_type === 'Cybersecurity') {
    return 'mdi-alert-outline'
  }
  return 'mdi-tag-outline'
}

export function tagTextFromType(tag_type) {
  if (tag_type === 'CVE_PRODUCT') {
    return 'Product'
  }
  if (tag_type === 'CVE_VENDOR') {
    return 'Vendor'
  }
  if (tag_type === 'ORG') {
    return 'Organization'
  }
  if (tag_type === 'LOC') {
    return 'Location'
  }
  if (tag_type === 'PER') {
    return 'Person'
  }
  if (tag_type === 'CySec') {
    return 'Cyber Security'
  }
  if (tag_type === 'cves') {
    return 'CVE'
  }
  if (tag_type === 'sha256s') {
    return 'SHA256'
  }
  if (tag_type === 'sha1s') {
    return 'SHA1'
  }
  if (tag_type === 'md5s') {
    return 'MD5'
  }
  if (tag_type === 'registry_key_paths') {
    return 'Registry Key Path'
  }
  if (tag_type === 'bitcoin_addresses') {
    return 'Bitcoin Address'
  }
  if (tag_type === 'MISC') {
    return 'Misc from NER'
  }
  if (tag_type === 'Cybersecurity') {
    return 'Various Cybersecurity from WordList'
  }
  return tag_type
}

export function getMessageFromError(error) {
  if (error.response && error.response.data && error.response.data.error) {
    return error.response.data.error
  }
  return error.message
}

export const baseFormat = [
  {
    name: 'id',
    label: 'ID',
    type: 'text',
    disabled: true
  },
  {
    name: 'name',
    label: 'Name',
    type: 'text'
  },
  {
    name: 'description',
    label: 'Description',
    type: 'textarea'
  }
]

export function removeRegexSpecialChars(string) {
  return string.replace(/[.*+?^${}()<>|[\]\\]/g, '')
}
export function highlight_text(content) {
  const filterStore = useFilterStore()
  if (!content) {
    return ''
  }
  let input = filterStore.newsItemsFilter.search
  if (filterStore.newsItemsFilter.tags?.length === 1) {
    input = input || filterStore.newsItemsFilter.tags[0]
  }
  if (!filterStore.highlight || !input) {
    return content
  }
  const term = removeRegexSpecialChars(input)
  let results = content
  results = results.replace(
    new RegExp(term, 'gi'),
    (match) => `<mark>${match}</mark>`
  )
  return results
}
