import { apiService } from '@/main'

export function getProfile() {
  return apiService.get('/users/profile')
}

export function updateProfile(data) {
  return apiService.put('/users/profile', data)
}

export function getUserDetails() {
  return apiService.get('/users/')
}

export function sseConnected() {
  return apiService.post('/users/sse-connected')
}
