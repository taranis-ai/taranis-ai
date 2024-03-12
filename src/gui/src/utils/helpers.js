import { useMainStore } from '@/stores/MainStore'
import { useFilterStore } from '@/stores/FilterStore'
import { useAssessStore } from '@/stores/AssessStore'

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

export function getSourceInfo(source) {
  const store = useAssessStore()
  if (!source) {
    return {}
  }
  return store.osint_sources.items.find((item) => item.id === source)
}

export function notifySuccess(text) {
  const successMessage =
    typeof text !== 'string' ? getMessageFromResponse(text) : text
  const store = useMainStore()
  store.notification = {
    type: 'success',
    message: successMessage,
    show: true
  }
}

export function notifyFailure(text) {
  const errorMessage =
    typeof text !== 'string' ? getMessageFromError(text) : text
  const store = useMainStore()
  store.notification = {
    type: 'red',
    message: errorMessage,
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

  format.forEach((item) => {
    if (!item || item.disabled) {
      return
    }
    newObject[item.name] = formDataDefaultValues(item.type)
  })

  return flattenFormData(newObject, format)
}

export function flattenFormData(data, format) {
  const flattened = {}
  const getValueOrDefault = (value, type) =>
    value === '' ? formDataDefaultValues(type) : value

  format.forEach(({ parent, name, type }) => {
    const key = parent ? `${parent}.${name}` : name
    if (parent) {
      data[parent] = data[parent] || {}

      flattened[key] = getValueOrDefault(data[parent][name], type)
    } else {
      flattened[key] = getValueOrDefault(data[name], type)
    }
  })

  return flattened
}

function formDataDefaultValues(format_type) {
  switch (format_type) {
    case 'switch':
      return false
    case 'text':
    case 'textarea':
    case 'select':
      return ''
    case 'number':
      return 0
    case 'table':
    case 'checkbox':
      return []
    default:
      return ''
  }
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

export function getMessageFromResponse(response) {
  if (response.data && response.data.message) {
    return response.data.message
  }
  return response.data
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
    type: 'text',
    rules: ['required']
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
export function markText(content, search) {
  if (!search || search.length === 0) {
    return content
  }
  const term = removeRegexSpecialChars(search)
  return content.replace(
    new RegExp(term, 'gi'),
    (match) => `<mark>${match}</mark>`
  )
}

export function highlight_text(content) {
  const filterStore = useFilterStore()
  if (!filterStore.highlight || !content) {
    return content
  }
  const input = []

  if (
    filterStore.newsItemsFilter.search &&
    filterStore.newsItemsFilter.search.length > 0
  ) {
    filterStore.newsItemsFilter.search.split(' ').forEach((word) => {
      input.push(word)
    })
  }
  if (
    filterStore.newsItemsFilter.tags &&
    filterStore.newsItemsFilter.tags.length > 0
  ) {
    filterStore.newsItemsFilter.tags.forEach((tag) => {
      input.push(tag)
    })
  }

  let results = content

  input.forEach((term) => {
    results = markText(results, term)
  })

  return results
}

export const tlpLevels = [
  { title: 'Clear', value: 'clear' },
  { title: 'Green', value: 'green' },
  { title: 'Amber', value: 'amber' },
  { title: 'Amber+Strict', value: 'amber+strict' },
  { title: 'Red', value: 'red' }
]
