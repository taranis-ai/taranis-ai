import ApiService from '@/services/api_service'

export function getDashboardData() {
  return ApiService.get('/dashboard-data')
}

export function getTrendingClusters() {
  return ApiService.get('/trending-clusters')
}

export function getCoreBuildInfo() {
  return ApiService.get('/build-info')
}
