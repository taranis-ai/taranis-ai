import { getApiService } from '@/services/api_service'

export function getAllAssetGroups(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/asset-groups?${filter}`)
}

export function getAssetGroup(asset_group_id) {
  return getApiService().get(`/asset-groups/${asset_group_id}`)
}

export function createAssetGroup(group) {
  return getApiService().post('/asset-groups', group)
}

export function updateAssetGroup(group) {
  return getApiService().put(`/asset-groups/${group}`, group)
}

export function deleteAssetGroup(group) {
  return getApiService().delete(`/asset-groups/${group}`)
}

export function getAllAssets(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/assets?${filter}`)
}

export function getAsset(asset_id) {
  return getApiService().get(`/assets/${asset_id}`)
}

export function createAsset(asset) {
  return getApiService().post('/assets', asset)
}

export function solveVulnerability(data) {
  return getApiService().post(
    `/assets/${data.asset_id}/vulnerabilities/${data.report_item_id}`,
    data
  )
}

export function updateAsset(asset) {
  return getApiService().put(`/assets/${asset}`, asset)
}

export function deleteAsset(asset) {
  return getApiService().delete(`/assets/${asset}`)
}

export function findAttributeCPE() {
  return getApiService().get('/asset-attributes/cpe')
}
