import { apiService } from '@/main'
import { parseJsonSourceFileConfigFileContent } from 'typescript'

export function getConflict(storyId) {
  return apiService.get(`/connectors/conflicts/compare/${storyId}`)
}

export function getAllConflicts() {
  return apiService.get(`/connectors/conflicts/compare`)
}

export function updateStory(storyId, resolutionData) {
  return apiService.patch(`/assess/story/${storyId}`, resolutionData)
}
