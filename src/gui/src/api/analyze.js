import { apiService } from '@/main'

export function getAllReportItems(filter) {
  return apiService.get(`/analyze/report-items?${filter}`)
}

export function getReportItem(report_item_id) {
  return apiService.get(`/analyze/report-items/${report_item_id}`)
}

export function createReportItem(data) {
  return apiService.post('/analyze/report-items', data)
}

export function cloneReportItem(report_item_id) {
  return apiService.post(`/analyze/report-items/${report_item_id}/clone`)
}

export function deleteReportItem(report_item_id) {
  return apiService.delete(`/analyze/report-items/${report_item_id}`)
}

export function updateReportItem(report_item_id, data) {
  return apiService.put(`/analyze/report-items/${report_item_id}`, data)
}

export function addStoriesToReportItem(report_item_id, data) {
  return apiService.post(
    `/analyze/report-items/${report_item_id}/stories`,
    data
  )
}

export function setStoriesToReportItem(report_item_id, data) {
  return apiService.put(`/analyze/report-items/${report_item_id}/stories`, data)
}

export function getReportItemLocks(report_item_id) {
  return apiService.get(`/analyze/report-items/${report_item_id}/locks`)
}

export function lockReportItem(report_item_id, data) {
  return apiService.put(`/analyze/report-items/${report_item_id}/lock`, data)
}

export function unlockReportItem(report_item_id, data) {
  return apiService.put(`/analyze/report-items/${report_item_id}/unlock`, data)
}

export function getAllReportTypes() {
  return apiService.get('/analyze/report-types')
}

export function getAttributeEnums(filter) {
  return apiService.get(
    `/analyze/report-item-attributes/${filter.attribute_id}/enums?search=${filter.search}&offset=${filter.offset}&limit=${filter.limit}`
  )
}

export function removeAttachment(data) {
  return apiService.delete(
    `/analyze/report-items/${data.report_item_id}/file-attributes/${data.attribute_id}`
  )
}
