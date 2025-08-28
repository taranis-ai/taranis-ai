import { getApiService } from '@/services/api_service'

export function authenticate(userData) {
  return getApiService().post('/auth/login', userData)
}

export function authRefresh() {
  return getApiService().get('/auth/refresh')
}

export function authLogout() {
  return getApiService().delete('/auth/logout')
}

export function getAuthMethod() {
  return getApiService().get('/auth/method')
}
