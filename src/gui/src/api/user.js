import { getApiService } from '@/services/api_service'

export function getProfile() {
  return getApiService().get('/users/profile')
}

export function updateProfile(data) {
  return getApiService().put('/users/profile', data)
}

export function getUserDetails() {
  return getApiService().get('/users/')
}

export function sseConnected() {
  return getApiService().post('/users/sse-connected')
}
