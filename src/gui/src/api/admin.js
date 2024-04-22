import { apiService } from '@/main'

export function getAdminSettings() {
  return apiService.get('/admin/')
}

export function updateAdminSettings(data) {
  return apiService.put('/admin/', data)
}

export function deleteAllTags() {
  return apiService.post('/admin/delete-tags')
}

export function clearQueues() {
  return apiService.post('/admin/clear-queues')
}

export function ungroupAllStories() {
  return apiService.post('/admin/ungroup-stories')
}

export function resetDatabase() {
  return apiService.post('/admin/reset-database')
}
