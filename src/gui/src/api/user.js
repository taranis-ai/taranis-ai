import { apiService } from '@/main'

export function getProfile() {
  return apiService.get('/users/profile')
}

export function updateProfile(data) {
  return apiService.put('/users/profile', data)
}

export function getAllUserProductTypes() {
  return apiService.get('/users/my-product-types')
}

export function getAllUserPublishersPresets() {
  return apiService.get('/users/my-publisher-presets')
}
