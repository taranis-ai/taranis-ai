import { apiService } from '@/main'

export function getAllAssetGroups(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/asset-groups?${filter}`)
}

export function getAssetGroup(asset_group_id) {
  return apiService.get(`/asset-groups/${asset_group_id}`)
}

export function createAssetGroup(group) {
  return apiService.post('/asset-groups', group)
}

export function updateAssetGroup(group) {
  return apiService.put(`/asset-groups/${group}`, group)
}

export function deleteAssetGroup(group) {
  return apiService.delete(`/asset-groups/${group}`)
}

export function getAllAssets(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/assets?${filter}`)
}

export function getAsset(asset_id) {
  return apiService.get(`/assets/${asset_id}`)
}

export function createAsset(asset) {
  return apiService.post('/assets', asset)
}

export function solveVulnerability(data) {
  return apiService.post(
    `/assets/${data.asset_id}/vulnerabilities/${data.report_item_id}`,
    data
  )
}

export function updateAsset(asset) {
  return apiService.put(`/assets/${asset}`, asset)
}

export function deleteAsset(asset) {
  return apiService.delete(`/assets/${asset}`)
}

export function findAttributeCPE() {
  return apiService.get('/asset-attributes/cpe')
}

export function getCPEAttributeEnums(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/asset-attributes/cpe/enums?${filter}`)
}
