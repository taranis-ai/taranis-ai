import { apiService } from '@/main'

export function getOSINTSourceGroupsList() {
  return apiService.get('/assess/osint-source-group-list')
}

export function getOSINTSourcesList() {
  return apiService.get('/assess/osint-sources-list')
}

export function getStories(filter) {
  return apiService.get(`/assess/stories?${filter}`)
}

export function getNewsItems(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/assess/news-items?${filter}`)
}

export function getTopStories() {
  return apiService.get('/assess/top-stories')
}

export function getTags(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/assess/taglist?${filter}`)
}

export function addNewsItem(data) {
  return apiService.post('/assess/news-items', data)
}

export function getNewsItem(news_item_id) {
  return apiService.get(`/assess/news-items/${news_item_id}`)
}

export function getStory(story_id) {
  return apiService.get(`/assess/story/${story_id}`)
}

export function voteStory(story_id, vote) {
  return apiService.put(`/assess/story/${story_id}`, {
    vote: vote
  })
}

export function updateStoryTags(story_id, tags) {
  return apiService.patch(`/assess/story/${story_id}`, {
    tags: tags
  })
}

export function patchNewsItem(news_item_id, data) {
  return apiService.patch(`/assess/news-items/${news_item_id}`, data)
}

export function updateNewsItemAttributes(news_item_id, attributes) {
  return apiService.put(
    `/assess/news-items/${news_item_id}/attributes`,
    attributes
  )
}

export function updateStory(story_id, data, user) {
  return apiService.put(`/assess/story/${story_id}`, data, user)
}

export function patchStory(story_id, data) {
  return apiService.patch(`/assess/story/${story_id}`, data)
}

export function readStory(story_id, read) {
  return apiService.put(`/assess/story/${story_id}`, {
    read: read
  })
}

export function deleteStory(story_id) {
  return apiService.delete(`/assess/story/${story_id}`)
}

export function importantStory(story_id, important) {
  return apiService.put(`/assess/story/${story_id}`, {
    important: important
  })
}

export function groupAction(data) {
  return apiService.put('/assess/stories/group', data)
}

export function unGroupAction(data) {
  return apiService.put('/assess/stories/ungroup', data)
}

export function unGroupNewsItems(data) {
  return apiService.put('/assess/news-items/ungroup', data)
}

export function deleteNewsItem(news_item_id) {
  return apiService.delete(`/assess/news-items/${news_item_id}`)
}

export function triggerBot(bot_id, story_id) {
  return apiService.post('/assess/stories/botactions', {
    bot_id: bot_id,
    story_id: story_id
  })
}

export function shareToConnector(connector_id, story_ids) {
  return apiService.post(`/assess/story/${connector_id}/share`, {
    story_ids: story_ids
  })
}
