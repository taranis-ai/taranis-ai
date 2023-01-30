import ApiService from '@/services/api_service'

export function reloadDictionaries (type) {
  return ApiService.get(`/config/reload-enum-dictionaries/${type}`)
}

export function getAllAttributes (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/attributes?${filter}`)
}

export function createAttribute (attribute) {
  return ApiService.post('/config/attributes', attribute)
}

export function updateAttribute (attribute) {
  return ApiService.put(`/config/attributes/${attribute.id}`, attribute)
}

export function deleteAttribute (attribute) {
  return ApiService.delete(`/config/attributes/${attribute.id}`)
}

export function getAttributeEnums (filter) {
  return ApiService.get(`/config/attributes/${filter.attribute_id}/enums?search=${filter.search}&offset=${filter.offset}&limit=${filter.limit}`)
}

export function addAttributeEnum (attribute_id, data) {
  return ApiService.post(`/config/attributes/${attribute_id}/enums`, data)
}

export function updateAttributeEnum (attribute_id, data) {
  return ApiService.put(`/config/attributes/${attribute_id}/enums/${data.id}`, data)
}

export function deleteAttributeEnum (attribute_id, attribute_enum_id) {
  return ApiService.delete(`/config/attributes/${attribute_id}/enums/${attribute_enum_id}`)
}

export function getAllReportItemTypes (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/report-item-types?${filter}`)
}

export function createReportItemType (report_item_type) {
  return ApiService.post('/config/report-item-types', report_item_type)
}

export function deleteReportItemType (report_item_type) {
  return ApiService.delete(`/config/report-item-types/${report_item_type.id}`)
}

export function updateReportItemType (report_item_type) {
  return ApiService.put(`/config/report-item-types/${report_item_type.id}`, report_item_type)
}

export function getAllProductTypes (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/product-types?${filter}`)
}

export function createProductType (product_type) {
  return ApiService.post('/config/product-types', product_type)
}

export function deleteProductType (product_type) {
  return ApiService.delete(`/config/product-types/${product_type.id}`)
}

export function updateProductType (product_type) {
  return ApiService.put(`/config/product-types/${product_type.id}`, product_type)
}

export function getAllPermissions (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/permissions?${filter}`)
}

export function getAllExternalPermissions (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/external-permissions?${filter}`)
}

export function getAllRoles (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/roles?${filter}`)
}

export function createRole (role) {
  return ApiService.post('/config/roles', role)
}

export function updateRole (role) {
  return ApiService.put(`/config/roles/${role.id}`, role)
}

export function deleteRole (role) {
  return ApiService.delete(`/config/roles/${role.id}`)
}

export function getAllCollectors (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/collectors?${filter}`)
}

export function getAllBots (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/bots?${filter}`)
}

export function getAllParameters (filter_data) {
  return ApiService.get('/config/parameters')
}

export function updateBot (bot) {
  return ApiService.put(`/config/bots/${bot.id}`, bot)
}

export function getAllACLEntries (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/acls?${filter}`)
}

export function createACLEntry (acl) {
  return ApiService.post('/config/acls', acl)
}

export function updateACLEntry (acl) {
  return ApiService.put(`/config/acls/${acl.id}`, acl)
}

export function deleteACLEntry (acl) {
  return ApiService.delete(`/config/acls/${acl.id}`)
}

export function getAllOrganizations (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/organizations?${filter}`)
}

export function createOrganization (organization) {
  return ApiService.post('/config/organizations', organization)
}

export function updateOrganization (organization) {
  const id = organization.id
  delete organization.id
  return ApiService.put(`/config/organizations/${id}`, organization)
}

export function deleteOrganization (organization) {
  return ApiService.delete(`/config/organizations/${organization.id}`)
}

export function getAllUsers (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/users?${filter}`)
}

export function createUser (user) {
  return ApiService.post('/config/users', user)
}

export function updateUser (user) {
  return ApiService.put(`/config/users/${user.id}`, user)
}

export function deleteUser (user) {
  return ApiService.delete(`/config/users/${user.id}`)
}

export function getAllExternalUsers (filter) {
  return ApiService.get(`/config/external-users?search=${filter.search}`)
}

export function createExternalUser (user) {
  return ApiService.post('/config/external-users', user)
}

export function updateExternalUser (user) {
  return ApiService.put(`/config/external-users/${user.id}`, user)
}

export function deleteExternalUser (user) {
  return ApiService.delete(`/config/external-users/${user.id}`)
}

export function getAllWordLists (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/word-lists?${filter}`)
}

export function createWordList (word_list) {
  return ApiService.post('/config/word-lists', word_list)
}

export function updateWordList (word_list) {
  return ApiService.put(`/config/word-lists/${word_list.id}`, word_list)
}

export function deleteWordList (word_list) {
  return ApiService.delete(`/config/word-lists/${word_list.id}`)
}

export function importWordList (form_data) {
  return ApiService.upload('/config/import-word-lists', form_data)
}

export function exportWordList (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.download(`/config/export-word-lists?${filter}`, 'word_lists_export.json')
}

export function getAllRemoteAccesses (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/remote-accesses?${filter}`)
}

export function createRemoteAccess (remote_access) {
  return ApiService.post('/config/remote-accesses', remote_access)
}

export function updateRemoteAccess (remote_access) {
  return ApiService.put(`/config/remote-accesses/${remote_access.id}`, remote_access)
}

export function deleteRemoteAccess (remote_access) {
  return ApiService.delete(`/config/remote-accesses/${remote_access.id}`)
}

export function getAllRemoteNodes (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/remote-nodes?${filter}`)
}

export function createRemoteNode (remote_node) {
  return ApiService.post('/config/remote-nodes', remote_node)
}

export function updateRemoteNode (remote_node) {
  return ApiService.put(`/config/remote-nodes/${remote_node.id}`, remote_node)
}

export function deleteRemoteNode (remote_node) {
  return ApiService.delete(`/config/remote-nodes/${remote_node.id}`)
}

export function connectRemoteNode (remote_node) {
  return ApiService.get(`/config/remote-nodes/${remote_node.id}/connect`)
}

export function getAllNodes (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/nodes?${filter}`)
}

export function triggerNode () {
  return ApiService.post('/config/collectors-nodes/refresh')
}

export function updateNode (node) {
  if (node.type === 'Collector') {
    return ApiService.put(`/config/collectors-nodes/${node.id}`, node)
  }
  if (node.type === 'Bot') {
    return ApiService.put(`/config/bots-nodes/${node.id}`, node)
  }
  if (node.type === 'Presenter') {
    return ApiService.put(`/config/presenters-nodes/${node.id}`, node)
  }
  if (node.type === 'Publisher') {
    return ApiService.put(`/config/publishers-nodes/${node.id}`, node)
  }
}

export function createNode (node) {
  if (node.type === 'Collector') {
    return ApiService.post('/config/collectors-nodes', node)
  }
  if (node.type === 'Bot') {
    return ApiService.post('/config/bots-nodes', node)
  }
  if (node.type === 'Presenter') {
    return ApiService.post('/config/presenters-nodes', node)
  }
  if (node.type === 'Publisher') {
    return ApiService.post('/config/publishers-nodes', node)
  }
}

export function deleteNode (node) {
  if (node.type === 'Collector') {
    return ApiService.delete(`/config/collectors-nodes/${node.id}`, node)
  }
  if (node.type === 'Bot') {
    return ApiService.delete(`/config/bots-nodes/${node.id}`, node)
  }
  if (node.type === 'Presenter') {
    return ApiService.delete(`/config/presenters-nodes/${node.id}`, node)
  }
  if (node.type === 'Publisher') {
    return ApiService.delete(`/config/publishers-nodes/${node.id}`, node)
  }
}

export function getAllOSINTSources (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/osint-sources?${filter}`)
}

export function createOSINTSource (source) {
  return ApiService.post('/config/osint-sources', source)
}

export function updateOSINTSource (source) {
  return ApiService.put(`/config/osint-sources/${source.id}`, source)
}

export function deleteOSINTSource (source) {
  return ApiService.delete(`/config/osint-sources/${source.id}`)
}

export function importOSINTSources (form_data) {
  return ApiService.upload('/config/import-osint-sources', form_data)
}

export function exportOSINTSources (filter_data) {
  return ApiService.download('/config/export-osint-sources', 'osint_sources_export.json')
}

export function getAllOSINTSourceGroups (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/osint-source-groups?${filter}`)
}

export function createOSINTSourceGroup (group) {
  return ApiService.post('/config/osint-source-groups', group)
}

export function updateOSINTSourceGroup (group) {
  return ApiService.put(`/config/osint-source-groups/${group.id}`, group)
}

export function deleteOSINTSourceGroup (group) {
  return ApiService.delete(`/config/osint-source-groups/${group.id}`)
}

export function getAllPublisherPresets (filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/config/publishers-presets?${filter}`)
}

export function createPublisherPreset (preset) {
  return ApiService.post('/config/publishers-presets', preset)
}

export function updatePublisherPreset (node) {
  return ApiService.put(`/config/publishers-presets/${node.id}`, node)
}

export function deletePublisherPreset (node) {
  return ApiService.delete(`/config/publishers-presets/${node.id}`)
}
