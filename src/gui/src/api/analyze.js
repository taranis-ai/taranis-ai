import { apiService } from '@/main'

export function getAllReportItems(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/analyze/report-items?${filter}`)
}

export function getReportItem(report_item_id) {
  return apiService.get(`/analyze/report-items/${report_item_id}`)
}

export function getReportItemData(report_item_id, data) {
  let params = ''
  if (data.update !== undefined) {
    params += `&update=${encodeURIComponent(data.update)}`
  }
  if (data.add !== undefined) {
    params += `&add=${encodeURIComponent(data.add)}`
  }
  if (data.title !== undefined) {
    params += `&title=${encodeURIComponent(data.title)}`
  }
  if (data.title_prefix !== undefined) {
    params += `&title_prefix=${encodeURIComponent(data.title_prefix)}`
  }
  if (data.attribute_id !== undefined) {
    params += `&attribute_id=${encodeURIComponent(data.attribute_id)}`
  }
  if (data.completed !== undefined) {
    params += `&completed=${encodeURIComponent(data.completed)}`
  }
  if (data.aggregate_ids !== undefined) {
    let aggregate_ids = ''
    for (const aggregate_id in data.aggregate_ids) {
      // FIXME(mw): this can probably be solved quicker with Array.reduce
      aggregate_ids += '--' + aggregate_id
    }
    aggregate_ids = aggregate_ids.replace('--', '')
    params += `&aggregate_ids=${encodeURIComponent(aggregate_ids)}`
  }

  params = params.replace('&', '?')

  return apiService.get(`/analyze/report-items/${report_item_id}/data${params}`)
}

export function createReportItem(data) {
  return apiService.post('/analyze/report-items', data)
}

export function deleteReportItem(report_item) {
  return apiService.delete(`/analyze/report-items/${report_item.id}`)
}

export function updateReportItem(report_item_id, data) {
  return apiService.put(`/analyze/report-items/${report_item_id}`, data)
}

export function addAggregatesToReportItem(report_item_id, data) {
  return apiService.post(
    `/analyze/report-items/${report_item_id}/aggregates`,
    data
  )
}

export function setAggregatesToReportItem(report_item_id, data) {
  return apiService.put(
    `/analyze/report-items/${report_item_id}/aggregates`,
    data
  )
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
