import { apiService } from '@/main'

export function getConflict(storyId) {
  return apiService.get(`/connectors/conflicts/compare/${storyId}`)
}

export function getAllStoryConflicts() {
  return apiService.get(`/connectors/conflicts/compare`)
}

export function getAllNewsItemConflicts() {
  return apiService.get(`/connectors/conflicts/newsitem/compare`)
}

export function getProposals() {
  return apiService.get(`/assess/connectors/proposals`)
}

export function updateStory(storyId, resolutionData) {
  return apiService.patch(`/assess/connectors/story/${storyId}`, resolutionData)
}

export async function fetchStorySummary(storyId) {
  const res = await apiService.get(`/connectors/story-summary/${storyId}`)
  return res.data
}
