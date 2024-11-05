import axios from 'axios'
import { useAuthStore } from '@/stores/AuthStore'
import { getQueryStringFromNestedObject } from '@/utils/query'

export class ApiService {
  constructor(baseURL) {
    this._axios = axios.create({
      baseURL: baseURL
    })
    this.authStore = useAuthStore()
    this.setHeader()
  }

  setHeader() {
    if (localStorage.ACCESS_TOKEN) {
      this._axios.defaults.headers.common.Authorization = `Bearer ${localStorage.ACCESS_TOKEN}`
    } else {
      this._axios.defaults.headers.common = {}
    }
  }

  getQueryStringFromNestedObject(filterObject) {
    return getQueryStringFromNestedObject(filterObject)
  }

  async get(resource) {
    return await this._axios.get(resource).catch((error) => {
      if (error.response.status === 401) {
        this.authStore.logout()
      }
      throw error
    })
  }

  async getBlob(resource) {
    return await this._axios.get(resource, {
      responseType: 'blob'
    })
  }

  post(resource, data) {
    return this._axios.post(resource, data)
  }

  put(resource, data) {
    return this._axios.put(resource, data)
  }

  patch(resource, data) {
    return this._axios.patch(resource, data)
  }

  delete(resource) {
    return this._axios.delete(resource)
  }

  upload(resource, form_data) {
    return this._axios.post(resource, form_data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

  async download(resource, file_name) {
    try {
      const response = await this._axios.get(resource, {
        responseType: 'blob'
      })
      const fileURL = window.URL.createObjectURL(new Blob([response.data]))
      const fileLink = document.createElement('a')
      fileLink.href = fileURL
      fileLink.setAttribute('download', file_name)
      document.body.appendChild(fileLink)
      fileLink.click()
      document.body.removeChild(fileLink)
    } catch (error) {
      console.error(error)
    }
  }
}
