import { apiService } from '@/main'

export function getConflict(storyId) {
  return apiService.get(`/conflicts/compare/${storyId}`)
}

export function resolveConflict(storyId, resolutionData) {
  return apiService.post(
    `/conflicts/compare/${storyId}/resolve`,
    resolutionData
  )
}

export function getAllConflicts() {
  return apiService.get(`/conflicts/compare`)
}
