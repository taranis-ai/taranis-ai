import ApiService from '@/services/api_service'

export function getAllAssetGroups(filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/asset-groups?${filter}`)
}

export function getAssetGroup(asset_group_id) {
  return ApiService.get(`/asset-groups/${asset_group_id}`)
}

export function createAssetGroup(group) {
  return ApiService.post('/asset-groups', group)
}

export function updateAssetGroup(group) {
  return ApiService.put(`/asset-groups/${group}`, group)
}

export function deleteAssetGroup(group) {
  return ApiService.delete(`/asset-groups/${group}`)
}

export function getAllAssets(filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/assets?${filter}`)
}

export function getAsset(asset_id) {
  return ApiService.get(`/assets/${asset_id}`)
}

export function createAsset(asset) {
  return ApiService.post('/assets', asset)
}

export function solveVulnerability(data) {
  return ApiService.post(
    `/assets/${data.asset_id}/vulnerabilities/${data.report_item_id}`,
    data
  )
}

export function updateAsset(asset) {
  return ApiService.put(`/assets/${asset}`, asset)
}

export function deleteAsset(asset) {
  return ApiService.delete(`/assets/${asset}`)
}

export function findAttributeCPE() {
  return ApiService.get('/asset-attributes/cpe')
}

export function getCPEAttributeEnums(filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/asset-attributes/cpe/enums?${filter}`)
}
