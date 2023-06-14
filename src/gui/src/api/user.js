import ApiService from '@/services/api_service'

export function getProfile() {
  return ApiService.get('/users/my-profile')
}

export function updateProfile(data) {
  return ApiService.put('/users/my-profile', data)
}

export function getAllUserProductTypes() {
  return ApiService.get('/users/my-product-types')
}

export function getAllUserPublishersPresets() {
  return ApiService.get('/users/my-publisher-presets')
}
