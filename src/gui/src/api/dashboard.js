import { apiService } from '@/main'

export function getDashboardData() {
  return apiService.get('/dashboard-data')
}

export function getTrendingClusters() {
  return apiService.get('/trending-clusters')
}

export function getCoreBuildInfo() {
  return apiService.get('/build-info')
}
