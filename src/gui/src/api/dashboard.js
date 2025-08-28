import { getApiService } from '@/services/api_service'

export function getDashboardData() {
  return getApiService().get('/dashboard')
}

export function getTrendingClusters(days = null) {
  if (days) {
    return getApiService().get(
      `/dashboard/trending-clusters?days=${days}&legacy=true`
    )
  }
  return getApiService().get('/dashboard/trending-clusters?legacy=true')
}

export function getClusterByType(tag_type, filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/dashboard/cluster/${tag_type}?${filter}`)
}

export function getCoreBuildInfo() {
  return getApiService().get('/dashboard/build-info')
}

export function deleteTag(tag_name) {
  return getApiService().delete(`/dashboard/delete-tag/${tag_name}`)
}
