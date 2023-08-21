import { useMainStore } from '@/stores/MainStore'

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
  if (tag_type === 'ORG') {
    return 'mdi-domain'
  }
  if (tag_type === 'LOC') {
    return 'mdi-map-marker'
  }
  if (tag_type === 'PER') {
    return 'mdi-account'
  }
  if (tag_type === 'CySec') {
    return 'mdi-shield-key'
  }
  return 'mdi-tag'
}

export function tagTextFromType(tag_type) {
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
  return 'Miscellaneous'
}

export function parseWordListEntries(entries) {
  if (entries.length === 0) {
    return [
      {
        title: 'No entries found',
        props: {
          subtitle: 'Please download a wordlist first'
        }
      }
    ]
  }
  entries.sort((a, b) => a.category.localeCompare(b.category))

  const output = []
  let lastCategory = null

  for (const item of entries) {
    if (item.category !== lastCategory) {
      output.push({ type: 'divider' })
      output.push({
        type: 'subheader',
        title: item.category,
        props: { color: 'primary' }
      })
      output.push({ type: 'divider' })
      lastCategory = item.category
    }
    output.push({
      title: item.value,
      props: {
        subtitle: item.description
      }
    })
  }

  return output
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
