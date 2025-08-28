import { getApiService } from '@/services/api_service'

export function getAllAttributes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/attributes?${filter}`)
}

export function createAttribute(attribute) {
  return getApiService().post('/config/attributes', attribute)
}

export function updateAttribute(attribute) {
  return getApiService().put(`/config/attributes/${attribute.id}`, attribute)
}

export function deleteAttribute(attribute) {
  return getApiService().delete(`/config/attributes/${attribute.id}`)
}

export function getAttributeEnums(filter) {
  return getApiService().get(
    `/config/attributes/${filter.attribute_id}/enums?search=${filter.search}&offset=${filter.offset}&limit=${filter.limit}`
  )
}

export function addAttributeEnum(attribute_id, data) {
  return getApiService().post(`/config/attributes/${attribute_id}/enums`, data)
}

export function updateAttributeEnum(attribute_id, data) {
  return getApiService().put(
    `/config/attributes/${attribute_id}/enums/${data.id}`,
    data
  )
}

export function deleteAttributeEnum(attribute_id, attribute_enum_id) {
  return getApiService().delete(
    `/config/attributes/${attribute_id}/enums/${attribute_enum_id}`
  )
}

export function getAllReportTypes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/report-item-types?${filter}`)
}

export function createReportItemType(report_item_type) {
  return getApiService().post('/config/report-item-types', report_item_type)
}

export function deleteReportItemType(report_item_type) {
  return getApiService().delete(
    `/config/report-item-types/${report_item_type.id}`
  )
}

export function updateReportItemType(report_item_type) {
  return getApiService().put(
    `/config/report-item-types/${report_item_type.id}`,
    report_item_type
  )
}

export function importReportTypes(form_data) {
  return getApiService().upload('/config/import-report-item-types', form_data)
}

export function exportReportTypes(filter) {
  return getApiService().download(
    `/config/export-report-item-types?${filter}`,
    'report_types_export.json'
  )
}

export function getAllTemplates(filter_data) {
  return getApiService().get(`/config/templates?list=true`)
}

export function deleteTemplate(template_path) {
  return getApiService().delete(`/config/templates/${template_path}`)
}

export function updateTemplate(template) {
  return getApiService().put('/config/templates', template)
}

export function getTemplate(template_path) {
  return getApiService().get(`/config/templates/${template_path}`)
}

export function getAllProductTypes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/product-types?${filter}`)
}

export function createProductType(product_type) {
  return getApiService().post('/config/product-types', product_type)
}

export function deleteProductType(product_type) {
  return getApiService().delete(`/config/product-types/${product_type.id}`)
}

export function updateProductType(product_type) {
  return getApiService().put(
    `/config/product-types/${product_type.id}`,
    product_type
  )
}

export function getProductType(product_type_id) {
  return getApiService().get(`/config/product-types/${product_type_id}`)
}

export function getAllPermissions(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/permissions?${filter}`)
}

export function getAllRoles(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/roles?${filter}`)
}

export function createRole(role) {
  return getApiService().post('/config/roles', role)
}

export function updateRole(role) {
  return getApiService().put(`/config/roles/${role.id}`, role)
}

export function deleteRole(role) {
  return getApiService().delete(`/config/roles/${role.id}`)
}

export function getAllWorkerTypes(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/worker-types?${filter}`)
}

export function patchWorkerType(worker_data) {
  return getApiService().patch(
    `/config/worker-types/${worker_data.id}`,
    worker_data
  )
}

export function getAllParameters() {
  return getApiService().get('/config/parameters')
}

export function getAllBots(bot) {
  return getApiService().get('/config/bots', bot)
}

export function createBot(bot) {
  return getApiService().post('/config/bots', bot)
}

export function updateBot(bot) {
  return getApiService().put(`/config/bots/${bot.id}`, bot)
}

export function deleteBot(bot) {
  return getApiService().delete(`/config/bots/${bot.id}`)
}

export function executeBotTask(bot_id) {
  return getApiService().post(`/config/bots/${bot_id}/execute`)
}

export function getAllACLEntries(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/acls?${filter}`)
}

export function createACLEntry(acl) {
  return getApiService().post('/config/acls', acl)
}

export function updateACLEntry(acl) {
  return getApiService().put(`/config/acls/${acl.id}`, acl)
}

export function deleteACLEntry(acl) {
  return getApiService().delete(`/config/acls/${acl.id}`)
}

export function getAllOrganizations(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/organizations?${filter}`)
}

export function createOrganization(organization) {
  return getApiService().post('/config/organizations', organization)
}

export function updateOrganization(organization) {
  return getApiService().put(
    `/config/organizations/${organization.id}`,
    organization
  )
}

export function deleteOrganization(organization) {
  return getApiService().delete(`/config/organizations/${organization.id}`)
}

export function getAllUsers(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/users?${filter}`)
}

export function createUser(user) {
  return getApiService().post('/config/users', user)
}

export function updateUser(user) {
  return getApiService().put(`/config/users/${user.id}`, user)
}

export function deleteUser(user) {
  return getApiService().delete(`/config/users/${user.id}`)
}

export function importUsers(form_data) {
  return getApiService().post('/config/users-import', form_data)
}

export function exportUsers(filter) {
  return getApiService().download(
    `/config/users-export?${filter}`,
    'users_export.json'
  )
}

export function getDetailedWordList(word_list_id) {
  return getApiService().get(`/config/word-lists/${word_list_id}`)
}

export function getAllWordLists(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/word-lists?${filter}`)
}

export function createWordList(word_list) {
  return getApiService().post('/config/word-lists', word_list)
}

export function updateWordList(word_list) {
  return getApiService().put(`/config/word-lists/${word_list.id}`, word_list)
}

export function deleteWordList(word_list) {
  return getApiService().delete(`/config/word-lists/${word_list.id}`)
}

export function importWordList(form_data) {
  return getApiService().upload('/config/import-word-lists', form_data)
}

export function exportWordList(filter) {
  return getApiService().download(
    `/config/export-word-lists?${filter}`,
    'word_lists_export.json'
  )
}

export function gatherWordListEntries(word_list) {
  return getApiService().put(`/config/word-lists/${word_list.id}/gather`)
}

export function getQueueStatus() {
  return getApiService().get('/config/workers/queue-status')
}

export function getQueueTasks() {
  return getApiService().get('/config/workers/tasks')
}

export function getAllSchedule() {
  return getApiService().get('/config/workers/schedule')
}

export function getNextFireOn(cronExpression) {
  return getApiService().post('/config/refresh-interval', {
    cron: cronExpression
  })
}

export function getAllWorkers() {
  return getApiService().get('/config/workers')
}

export function getAllOSINTSources(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/osint-sources?${filter}`)
}

export function createOSINTSource(source) {
  return getApiService().post('/config/osint-sources', source)
}

export function collectOSINTSSource(source_id) {
  return getApiService().post(`/config/osint-sources/${source_id}/collect`)
}

export function previewOSINTSSource(source_id) {
  return getApiService().post(`/config/osint-sources/${source_id}/preview`)
}

export function toggleOSINTSSource(source_id, action) {
  return getApiService().patch(
    `/config/osint-sources/${source_id}?state=${action}`
  )
}

export function getOSINTSSourcePreview(source_id) {
  return getApiService().get(`/config/osint-sources/${source_id}/preview`)
}

export function collectAllOSINTSSources() {
  return getApiService().post('/config/osint-sources/collect')
}

export function updateOSINTSource(source) {
  return getApiService().put(`/config/osint-sources/${source.id}`, source)
}

export function deleteOSINTSource(source, force = false) {
  const force_query = force ? '?force=true' : ''
  return getApiService().delete(
    `/config/osint-sources/${source.id}${force_query}`
  )
}

export function importOSINTSources(form_data) {
  return getApiService().upload('/config/import-osint-sources', form_data)
}

export function exportOSINTSources(filter) {
  return getApiService().download(
    `/config/export-osint-sources?${filter}`,
    'osint_sources_export.json'
  )
}

export function getAllOSINTSourceGroups(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/osint-source-groups?${filter}`)
}

export function createOSINTSourceGroup(group) {
  return getApiService().post('/config/osint-source-groups', group)
}

export function updateOSINTSourceGroup(group) {
  return getApiService().put(`/config/osint-source-groups/${group.id}`, group)
}

export function deleteOSINTSourceGroup(group) {
  return getApiService().delete(`/config/osint-source-groups/${group.id}`)
}

export function getAllPublisher(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/publishers-presets?${filter}`)
}

export function createPublisher(preset) {
  return getApiService().post('/config/publishers-presets', preset)
}

export function updatePublisher(node) {
  return getApiService().put(`/config/publishers-presets/${node.id}`, node)
}

export function deletePublisher(node) {
  return getApiService().delete(`/config/publishers-presets/${node.id}`)
}

export function getAllConnectors(filter_data) {
  const filter = apiService.getQueryStringFromNestedObject(filter_data)
  return getApiService().get(`/config/connectors?${filter}`)
}

export function createConnector(connector) {
  return getApiService().post('/config/connectors', connector)
}

export function updateConnector(connector) {
  return getApiService().put(`/config/connectors/${connector.id}`, connector)
}
