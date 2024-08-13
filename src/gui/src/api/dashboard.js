import { apiService } from '@/main'

export function getDashboardData() {
  return apiService.get('/dashboard')
}

export function getTrendingClusters(days = null) {
  if (days) {
    return apiService.get(`/dashboard/trending-clusters?days=${days}`)
  }
  return apiService.get('/dashboard/trending-clusters')
}

export function getClusterByType(tag_type, filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/dashboard/cluster/${tag_type}?${filter}`)
}

export function getCoreBuildInfo() {
  return apiService.get('/dashboard/build-info')
}

export function deleteTag(tag_name) {
  return apiService.delete(`/dashboard/delete-tag/${tag_name}`)
}
