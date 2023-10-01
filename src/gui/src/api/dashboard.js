import { apiService } from '@/main'

export function getDashboardData() {
  return apiService.get('/dashboard')
}

export function getTrendingClusters() {
  return apiService.get('/dashboard/trending-clusters')
}

export function getCluster(tag_type, filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/dashboard/cluster/${tag_type}?${filter}`)
}

export function getCoreBuildInfo() {
  return apiService.get('/dashboard/build-info')
}
