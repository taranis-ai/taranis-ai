import { router } from '@/router'
import ApiService from '@/services/api_service'

export function getOSINTSourceGroupsList() {
  return ApiService.get('/assess/osint-source-group-list')
}

export function getOSINTSourcesList() {
  return ApiService.get('/assess/osint-sources-list')
}

export function getManualOSINTSources() {
  return ApiService.get('/assess/manual-osint-sources')
}

export function getNewsItemsAggregates(filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  router.push({ query: filter_data })
  return ApiService.get(`/assess/news-item-aggregates?${filter}`)
}

export function getNewsItems(filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/assess/news-items?${filter}`)
}

export function getTopStories() {
  return ApiService.get('/assess/top-stories')
}

export function getTags(filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/assess/tags?${filter}`)
}

export function addNewsItem(data) {
  return ApiService.post('/assess/news-items', data)
}

export function getNewsItem(news_item_id) {
  return ApiService.get(`/assess/news-items/${news_item_id}`)
}

export function getNewsItemAggregate(aggregate_id) {
  return ApiService.get(`/assess/news-item-aggregates/${aggregate_id}`)
}

export function voteNewsItemAggregate(aggregate_id, vote) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, {
    vote: vote
  })
}

export function readNewsItemAggregate(aggregate_id) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, {
    read: true
  })
}

export function deleteNewsItemAggregate(aggregate_id) {
  return ApiService.delete(`/assess/news-item-aggregates/${aggregate_id}`)
}

export function importantNewsItemAggregate(aggregate_id) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, {
    important: true
  })
}

export function groupAction(data) {
  return ApiService.put('/assess/news-item-aggregates/group', data)
}

export function unGroupAction(data) {
  return ApiService.put('/assess/news-item-aggregates/ungroup', data)
}

export function saveNewsItemAggregate(
  group_id,
  aggregate_id,
  title,
  description,
  comments
) {
  return ApiService.put(`/assess/news-item-aggregates/${aggregate_id}`, {
    group_id: group_id,
    title: title,
    description: description,
    comments: comments
  })
}

export function voteNewsItem(group_id, news_item_id, vote) {
  return ApiService.put(`/assess/news-items/${news_item_id}`, {
    group_id: group_id,
    vote: vote
  })
}

export function readNewsItem(group_id, news_item_id) {
  return ApiService.put(`/assess/news-items/${news_item_id}`, {
    group_id: group_id,
    read: true
  })
}

export function deleteNewsItem(group_id, news_item_id) {
  return ApiService.delete(`/assess/news-items/${news_item_id}`)
}

export function importantNewsItem(group_id, news_item_id) {
  return ApiService.put(`/assess/news-items/${news_item_id}`, {
    group_id: group_id,
    important: true
  })
}
