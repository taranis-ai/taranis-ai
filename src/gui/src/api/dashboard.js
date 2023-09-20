import { apiService } from '@/main'

export function getDashboardData() {
  return apiService.get('/dashboard')
}

export function getTrendingClusters() {
  return apiService.get('/dashboard/trending-clusters')
}

export function getCoreBuildInfo() {
  return apiService.get('/dashboard/build-info')
}
