import axios from 'axios'

const ApiService = {
  init(baseURL) {
    axios.defaults.baseURL = baseURL
    ApiService.setHeader()
  },

  setHeader() {
    if (localStorage.ACCESS_TOKEN) {
      axios.defaults.headers.common.Authorization = `Bearer ${localStorage.ACCESS_TOKEN}`
    } else {
      axios.defaults.headers.common = {}
    }
  },

  getQueryStringFromObject(filterObject) {
    return Object.entries(filterObject)
      .filter(([, val]) => val != null)
      .map(([key, val]) => `${key}=${val}`)
      .join('&')
  },

  getQueryStringFromNestedObject(filterObject) {
    if (filterObject == null) {
      return ''
    }
    return Object.entries(filterObject)
      .filter(([, val]) => val != null)
      .map(function ([key, val]) {
        if (Array.isArray(val)) {
          return val.map((v) => `${key}=${v}`).join('&')
        }
        if (typeof val === 'object') {
          return ApiService.getQueryStringFromObject(val)
        }
        return `${key}=${val}`
      })
      .join('&')
  },

  get(resource) {
    return axios.get(resource)
  },

  post(resource, data) {
    return axios.post(resource, data)
  },

  put(resource, data) {
    return axios.put(resource, data)
  },

  delete(resource) {
    return axios.delete(resource)
  },

  upload(resource, form_data) {
    return axios.post(resource, form_data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  download(resource, file_name) {
    axios
      .get(resource, {
        responseType: 'blob'
      })
      .then((response) => {
        const fileURL = window.URL.createObjectURL(new Blob([response.data]))
        const fileLink = document.createElement('a')
        fileLink.href = fileURL
        fileLink.setAttribute('download', file_name)
        document.body.appendChild(fileLink)
        fileLink.click()
        document.body.removeChild(fileLink)
      })
      .catch((error) => {
        console.error(error)
      })
  }
}

export default ApiService
