import ApiService from '@/services/api_service'

export function getAllAssetGroups (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/my-assets/asset-groups?${filter}`)
}

export function createAssetGroup (group) {
  return ApiService.post('/my-assets/asset-groups', group)
}

export function updateAssetGroup (group) {
  return ApiService.put(`/my-assets/asset-groups/${group.id}`, group)
}

export function deleteAssetGroup (group) {
  return ApiService.delete(`/my-assets/asset-groups/${group.id}`)
}

export function getAllNotificationTemplates (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/my-assets/asset-notification-templates?${filter}`)
}

export function createNotificationTemplate (template) {
  return ApiService.post('/my-assets/asset-notification-templates', template)
}

export function updateNotificationTemplate (template) {
  return ApiService.put(`/my-assets/asset-notification-templates/${template.id}`, template)
}

export function deleteNotificationTemplate (template) {
  return ApiService.delete(`/my-assets/asset-notification-templates/${template.id}`)
}

export function getAllAssets (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/assets?${filter}`)
}

export function getAsset (asset_id) {
  return ApiService.get(`/asset/${asset_id}`)
}

export function createAsset (asset) {
  return ApiService.post(`/my-assets/asset-groups/${asset.asset_group_id}/assets`, asset)
}

export function solveVulnerability (data) {
  return ApiService.post(`/my-assets/asset-groups/${data.group_id}/assets/${data.asset_id}/vulnerabilities/${data.report_item_id}`, data)
}

export function updateAsset (asset) {
  return ApiService.put(`/my-assets/asset-groups/${asset.asset_group_id}/assets/${asset.id}`, asset)
}

export function deleteAsset (asset) {
  return ApiService.delete(`/my-assets/asset-groups/${asset.asset_group_id}/assets/${asset.id}`)
}

export function findAttributeCPE () {
  return ApiService.get('/my-assets/attributes/cpe')
}

export function getCPEAttributeEnums (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/my-assets/attributes/cpe/enums?${filter}`)
}
