import { apiService } from '@/main'

export function getConflict(storyId) {
  return apiService.get(`/connectors/conflicts/stories/${storyId}`)
}

export function getAllStoryConflicts() {
  return apiService.get(`/connectors/conflicts/stories`)
}

export function getAllNewsItemConflicts() {
  return apiService.get(`/connectors/conflicts/news-items`)
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

export function resolveIngestIncomingStory(storyIds) {
  return apiService.put('/connectors/conflicts/news-items', storyIds, {
    headers: { 'Content-Type': 'application/json' }
  })
}

export function resolveAddUniqueNewsItems(payload) {
  return apiService.post('/connectors/news-items', payload, {
    headers: { 'Content-Type': 'application/json' }
  })
}
