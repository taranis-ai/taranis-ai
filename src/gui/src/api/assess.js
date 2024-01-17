import { router } from '@/router'
import { apiService } from '@/main'

export function getOSINTSourceGroupsList() {
  return apiService.get('/assess/osint-source-group-list')
}

export function getOSINTSourcesList() {
  return apiService.get('/assess/osint-sources-list')
}

export function getNewsItemsAggregates(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  router.push({ query: filter_data })
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
  return apiService.get(`/assess/tags?${filter}`)
}

export function addNewsItem(data) {
  return apiService.post('/assess/news-items', data)
}

export function getNewsItem(news_item_id) {
  return apiService.get(`/assess/news-items/${news_item_id}`)
}

export function getNewsItemAggregate(aggregate_id) {
  return apiService.get(`/assess/stories/${aggregate_id}`)
}

export function voteNewsItemAggregate(aggregate_id, vote) {
  return apiService.put(`/assess/stories/${aggregate_id}`, {
    vote: vote
  })
}

export function updateStoryTags(aggregate_id, tags) {
  return apiService.patch(`/assess/stories/${aggregate_id}`, {
    tags: tags
  })
}

export function readNewsItemAggregate(aggregate_id, read) {
  return apiService.put(`/assess/stories/${aggregate_id}`, {
    read: read
  })
}

export function deleteNewsItemAggregate(aggregate_id) {
  return apiService.delete(`/assess/stories/${aggregate_id}`)
}

export function importantNewsItemAggregate(aggregate_id, important) {
  return apiService.put(`/assess/stories/${aggregate_id}`, {
    important: important
  })
}

export function groupAction(data) {
  return apiService.put('/assess/stories/group', data)
}

export function unGroupStories(data) {
  return apiService.put('/assess/stories/ungroup', data)
}

export function unGroupNewsItems(data) {
  return apiService.put('/assess/news-items/ungroup', data)
}

export function saveNewsItemAggregate(
  group_id,
  aggregate_id,
  title,
  description,
  comments
) {
  return apiService.put(`/assess/stories/${aggregate_id}`, {
    group_id: group_id,
    title: title,
    description: description,
    comments: comments
  })
}

export function voteNewsItem(group_id, news_item_id, vote) {
  return apiService.put(`/assess/news-items/${news_item_id}`, {
    group_id: group_id,
    vote: vote
  })
}

export function readNewsItem(group_id, news_item_id) {
  return apiService.put(`/assess/news-items/${news_item_id}`, {
    group_id: group_id,
    read: true
  })
}

export function deleteNewsItem(group_id, news_item_id) {
  return apiService.delete(`/assess/news-items/${news_item_id}`)
}

export function importantNewsItem(group_id, news_item_id) {
  return apiService.put(`/assess/news-items/${news_item_id}`, {
    group_id: group_id,
    important: true
  })
}
