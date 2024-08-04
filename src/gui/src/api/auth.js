import { apiService } from '@/main'

export function authenticate(userData) {
  return apiService.post('/auth/login', userData)
}

export function authRefresh() {
  return apiService.get('/auth/refresh')
}

export function authLogout() {
  return apiService.delete('/auth/logout')
}

export function getAuthMethod() {
  return apiService.get('/auth/method')
}
