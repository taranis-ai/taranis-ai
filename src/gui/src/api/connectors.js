import { getApiService } from '@/services/api_service'

export function getConflict(storyId) {
  return getApiService().get(`/connectors/conflicts/compare/${storyId}`)
}

export function getAllStoryConflicts() {
  return getApiService().get(`/connectors/conflicts/compare`)
}

export function getAllNewsItemConflicts() {
  return getApiService().get(`/connectors/conflicts/newsitem/compare`)
}

export function getProposals() {
  return getApiService().get(`/assess/connectors/proposals`)
}

export function updateStory(storyId, resolutionData) {
  return getApiService().patch(
    `/assess/connectors/story/${storyId}`,
    resolutionData
  )
}

export async function fetchStorySummary(storyId) {
  const res = await apiService.get(`/connectors/story-summary/${storyId}`)
  return res.data
}

export async function submitNewsItemConflictResolution(resolutionData) {
  return getApiService().post('/connectors/conflict/resolve', resolutionData, {
    headers: {
      'Content-Type': 'application/json'
    }
  })
}
