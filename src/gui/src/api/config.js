import { apiService } from '@/main'

export function reloadDictionaries(type) {
  return apiService.get(`/config/reload-enum-dictionaries/${type}`)
}

export function getAllAttributes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/attributes?${filter}`)
}

export function createAttribute(attribute) {
  return apiService.post('/config/attributes', attribute)
}

export function updateAttribute(attribute) {
  return apiService.put(`/config/attributes/${attribute.id}`, attribute)
}

export function deleteAttribute(attribute) {
  return apiService.delete(`/config/attributes/${attribute.id}`)
}

export function getAttributeEnums(filter) {
  return apiService.get(
    `/config/attributes/${filter.attribute_id}/enums?search=${filter.search}&offset=${filter.offset}&limit=${filter.limit}`
  )
}

export function addAttributeEnum(attribute_id, data) {
  return apiService.post(`/config/attributes/${attribute_id}/enums`, data)
}

export function updateAttributeEnum(attribute_id, data) {
  return apiService.put(
    `/config/attributes/${attribute_id}/enums/${data.id}`,
    data
  )
}

export function deleteAttributeEnum(attribute_id, attribute_enum_id) {
  return apiService.delete(
    `/config/attributes/${attribute_id}/enums/${attribute_enum_id}`
  )
}

export function getAllReportTypes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/report-item-types?${filter}`)
}

export function createReportItemType(report_item_type) {
  return apiService.post('/config/report-item-types', report_item_type)
}

export function deleteReportItemType(report_item_type) {
  return apiService.delete(`/config/report-item-types/${report_item_type.id}`)
}

export function updateReportItemType(report_item_type) {
  return apiService.put(
    `/config/report-item-types/${report_item_type.id}`,
    report_item_type
  )
}

export function getAllProductTypes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/product-types?${filter}`)
}

export function createProductType(product_type) {
  return apiService.post('/config/product-types', product_type)
}

export function deleteProductType(product_type) {
  return apiService.delete(`/config/product-types/${product_type.id}`)
}

export function updateProductType(product_type) {
  return apiService.put(
    `/config/product-types/${product_type.id}`,
    product_type
  )
}

export function getAllPermissions(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/permissions?${filter}`)
}

export function getAllRoles(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/roles?${filter}`)
}

export function createRole(role) {
  return apiService.post('/config/roles', role)
}

export function updateRole(role) {
  return apiService.put(`/config/roles/${role.id}`, role)
}

export function deleteRole(role) {
  return apiService.delete(`/config/roles/${role.id}`)
}

export function getAllWorkerTypes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/worker-types?${filter}`)
}

export function getAllParameters() {
  return apiService.get('/config/parameters')
}

export function getAllBots(bot) {
  return apiService.get('/config/bots', bot)
}

export function createBot(bot) {
  return apiService.post('/config/bots', bot)
}

export function updateBot(bot) {
  return apiService.put(`/config/bots/${bot.id}`, bot)
}

export function deleteBot(bot) {
  return apiService.delete(`/config/bots/${bot.id}`)
}

export function executeBotTask(bot_id) {
  return apiService.post(`/config/bots/${bot_id}/execute`)
}

export function getAllACLEntries(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/acls?${filter}`)
}

export function createACLEntry(acl) {
  return apiService.post('/config/acls', acl)
}

export function updateACLEntry(acl) {
  return apiService.put(`/config/acls/${acl.id}`, acl)
}

export function deleteACLEntry(acl) {
  return apiService.delete(`/config/acls/${acl.id}`)
}

export function getAllOrganizations(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/organizations?${filter}`)
}

export function createOrganization(organization) {
  return apiService.post('/config/organizations', organization)
}

export function updateOrganization(organization) {
  const { id } = organization
  return apiService.put(`/config/organizations/${id}`, organization)
}

export function deleteOrganization(organization) {
  return apiService.delete(`/config/organizations/${organization.id}`)
}

export function getAllUsers(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/users?${filter}`)
}

export function createUser(user) {
  return apiService.post('/config/users', user)
}

export function updateUser(user) {
  return apiService.put(`/config/users/${user.id}`, user)
}

export function deleteUser(user) {
  return apiService.delete(`/config/users/${user.id}`)
}

export function getAllWordLists(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/word-lists?${filter}`)
}

export function createWordList(word_list) {
  return apiService.post('/config/word-lists', word_list)
}

export function updateWordList(word_list) {
  return apiService.put(`/config/word-lists/${word_list.id}`, word_list)
}

export function deleteWordList(word_list) {
  return apiService.delete(`/config/word-lists/${word_list.id}`)
}

export function importWordList(form_data) {
  return apiService.upload('/config/import-word-lists', form_data)
}

export function gatherWordListEntries(word_list) {
  return apiService.put(`/config/word-lists/${word_list.id}/gather`)
}

export function exportWordList(filter) {
  return apiService.download(
    `/config/export-word-lists?${filter}`,
    'word_lists_export.json'
  )
}

export function getQueueStatus() {
  return apiService.get('/config/workers/queue-status')
}

export function getAllSchedule() {
  return apiService.get('/config/workers/schedule')
}

export function getAllWorkers() {
  return apiService.get('/config/workers')
}

export function getAllOSINTSources(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/osint-sources?${filter}`)
}

export function createOSINTSource(source) {
  return apiService.post('/config/osint-sources', source)
}

export function collectOSINTSSource(source_id) {
  return apiService.post(`/config/osint-sources/${source_id}/collect`)
}

export function collectAllOSINTSSources() {
  return apiService.post('/config/osint-sources/collect')
}

export function updateOSINTSource(source) {
  return apiService.put(`/config/osint-sources/${source.id}`, source)
}

export function deleteOSINTSource(source) {
  return apiService.delete(`/config/osint-sources/${source.id}`)
}

export function importOSINTSources(form_data) {
  return apiService.upload('/config/import-osint-sources', form_data)
}

export function exportOSINTSources(filter) {
  return apiService.download(
    `/config/export-osint-sources?${filter}`,
    'osint_sources_export.json'
  )
}

export function getAllOSINTSourceGroups(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/osint-source-groups?${filter}`)
}

export function createOSINTSourceGroup(group) {
  return apiService.post('/config/osint-source-groups', group)
}

export function updateOSINTSourceGroup(group) {
  return apiService.put(`/config/osint-source-groups/${group.id}`, group)
}

export function deleteOSINTSourceGroup(group) {
  return apiService.delete(`/config/osint-source-groups/${group.id}`)
}

export function getAllPublisherPresets(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return apiService.get(`/config/publishers-presets?${filter}`)
}

export function createPublisherPreset(preset) {
  return apiService.post('/config/publishers-presets', preset)
}

export function updatePublisherPreset(node) {
  return apiService.put(`/config/publishers-presets/${node.id}`, node)
}

export function deletePublisherPreset(node) {
  return apiService.delete(`/config/publishers-presets/${node.id}`)
}
