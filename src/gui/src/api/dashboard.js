import ApiService from '@/services/api_service'

export function getDashboardData () {
  return ApiService.get('/dashboard-data')
}
