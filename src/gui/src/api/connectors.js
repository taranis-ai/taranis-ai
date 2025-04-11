import { apiService } from '@/main'
import { parseJsonSourceFileConfigFileContent } from 'typescript'

export function getConflict(storyId) {
  return apiService.get(`/connectors/conflicts/compare/${storyId}`)
}

export function resolveConflict(storyId, resolutionData) {
  // TODO: implement an update endpoint that would update the internal conflicting stories
}

export function getAllConflicts() {
  return apiService.get(`/connectors/conflicts/compare`)
}
