import { apiService } from '@/main'

export function getDefaultSoures() {
  return apiService.getBlob('/static/default_sources.json')
}

export function getDefaultWordLists() {
  return apiService.getBlob('/static/default_word_lists.json')
}
