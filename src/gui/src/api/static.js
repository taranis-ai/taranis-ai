import { getApiService } from '@/services/api_service'

export function getDefaultSoures() {
  return getApiService().getBlob('/static/default_sources.json')
}

export function getDefaultWordLists() {
  return getApiService().getBlob('/static/default_word_lists.json')
}
