import { apiService } from '@/main'

export function getConflict(storyId) {
  return apiService.get(`/connectors/conflicts/compare/${storyId}`)
}

export function getAllConflicts() {
  return apiService.get(`/connectors/conflicts/compare`)
}

export function getProposals() {
  return apiService.get(`/assess/connectors/proposals`)
}

export function updateStory(storyId, resolutionData) {
  return apiService.patch(`/assess/connectors/story/${storyId}`, resolutionData)
}
