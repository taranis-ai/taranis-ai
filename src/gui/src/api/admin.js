import { getApiService } from '@/services/api_service'

export function getAdminSettings() {
  return getApiService().get('/admin/')
}

export function updateAdminSettings(data) {
  return getApiService().put('/admin/', data)
}

export function deleteAllTags() {
  return getApiService().post('/admin/delete-tags')
}

export function clearQueues() {
  return getApiService().post('/admin/clear-queues')
}

export function ungroupAllStories() {
  return getApiService().post('/admin/ungroup-stories')
}

export function resetDatabase() {
  return getApiService().post('/admin/reset-database')
}
