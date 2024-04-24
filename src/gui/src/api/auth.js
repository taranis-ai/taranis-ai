import { apiService } from '@/main'

export function authenticate(userData) {
  return apiService.post('/auth/login', userData)
}

export function authRefresh() {
  return apiService.get('/auth/refresh')
}
