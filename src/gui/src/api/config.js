import ApiService from "@/services/api_service";

export function reloadDictionaries(type) {
    return ApiService.get('/config/reload-enum-dictionaries/' + type)
}

export function getAllAttributes(filter) {
    return ApiService.get('/config/attributes?search=' + filter.search)
}

export function createNewAttribute(attribute) {
    return ApiService.post('/config/attributes', attribute)
}

export function updateAttribute(attribute) {
    return ApiService.put('/config/attributes/' + attribute.id, attribute)
}

export function deleteAttribute(attribute) {
    return ApiService.delete('/config/attributes/' + attribute.id)
}

export function getAttributeEnums(filter) {
    return ApiService.get('/config/attributes/' + filter.attribute_id + '/enums?search=' + filter.search + '&offset=' + filter.offset + '&limit=' + filter.limit)
}

export function addAttributeEnum(attribute_id, data) {
    return ApiService.post('/config/attributes/' + attribute_id + '/enums', data)
}

export function updateAttributeEnum(attribute_id, data) {
    return ApiService.put('/config/attributes/' + attribute_id + '/enums/' + data.id, data)
}

export function deleteAttributeEnum(attribute_id, attribute_enum_id) {
    return ApiService.delete('/config/attributes/' + attribute_id + '/enums/' + attribute_enum_id)
}

export function getAllReportItemTypes(filter) {
    return ApiService.get('/config/report-item-types?search=' + filter.search)
}

export function createNewReportItemType(report_item_type) {
    return ApiService.post('/config/report-item-types', report_item_type)
}

export function deleteReportItemType(report_item_type) {
    return ApiService.delete('/config/report-item-types/' + report_item_type.id)
}

export function updateReportItemType(report_item_type) {
    return ApiService.put('/config/report-item-types/' + report_item_type.id, report_item_type)
}

export function getAllProductTypes(filter) {
    return ApiService.get('/config/product-types?search=' + filter.search)
}

export function createNewProductType(product_type) {
    return ApiService.post('/config/product-types', product_type)
}

export function deleteProductType(product_type) {
    return ApiService.delete('/config/product-types/' + product_type.id)
}

export function updateProductType(product_type) {
    return ApiService.put('/config/product-types/' + product_type.id, product_type)
}

export function getAllPermissions(filter) {
    return ApiService.get('/config/permissions?search=' + filter.search)
}

export function getAllExternalPermissions(filter) {
    return ApiService.get('/config/external-permissions?search=' + filter.search)
}

export function getAllRoles(filter) {
    return ApiService.get('/config/roles?search=' + filter.search)
}

export function createNewRole(role) {
    return ApiService.post('/config/roles', role)
}

export function updateRole(role) {
    return ApiService.put('/config/roles/' + role.id, role)
}

export function deleteRole(role) {
    return ApiService.delete('/config/roles/' + role.id)
}

export function getAllACLEntries(filter) {
    return ApiService.get('/config/acls?search=' + filter.search)
}

export function createNewACLEntry(acl) {
    return ApiService.post('/config/acls', acl)
}

export function updateACLEntry(acl) {
    return ApiService.put('/config/acls/' + acl.id, acl)
}

export function deleteACLEntry(acl) {
    return ApiService.delete('/config/acls/' + acl.id)
}

export function getAllOrganizations(filter) {
    return ApiService.get('/config/organizations?search=' + filter.search)
}

export function createNewOrganization(organization) {
    return ApiService.post('/config/organizations', organization)
}

export function updateOrganization(organization) {
    return ApiService.put('/config/organizations/' + organization.id, organization)
}

export function deleteOrganization(organization) {
    return ApiService.delete('/config/organizations/' + organization.id)
}

export function getAllUsers(filter) {
    return ApiService.get('/config/users?search=' + filter.search)
}

export function createNewUser(user) {
    return ApiService.post('/config/users', user)
}

export function updateUser(user) {
    return ApiService.put('/config/users/' + user.id, user)
}

export function deleteUser(user) {
    return ApiService.delete('/config/users/' + user.id)
}

export function getAllExternalUsers(filter) {
    return ApiService.get('/config/external-users?search=' + filter.search)
}

export function createNewExternalUser(user) {
    return ApiService.post('/config/external-users', user)
}

export function updateExternalUser(user) {
    return ApiService.put('/config/external-users/' + user.id, user)
}

export function deleteExternalUser(user) {
    return ApiService.delete('/config/external-users/' + user.id)
}

export function getAllWordLists(filter) {
    return ApiService.get('/config/word-lists?search=' + filter.search)
}

export function createNewWordList(word_list) {
    return ApiService.post('/config/word-lists', word_list)
}

export function updateWordList(word_list) {
    return ApiService.put('/config/word-lists/' + word_list.id, word_list)
}

export function deleteWordList(word_list) {
    return ApiService.delete('/config/word-lists/' + word_list.id)
}

export function getAllRemoteAccesses(filter) {
    return ApiService.get('/config/remote-accesses?search=' + filter.search)
}

export function createNewRemoteAccess(remote_access) {
    return ApiService.post('/config/remote-accesses', remote_access)
}

export function updateRemoteAccess(remote_access) {
    return ApiService.put('/config/remote-accesses/' + remote_access.id, remote_access)
}

export function deleteRemoteAccess(remote_access) {
    return ApiService.delete('/config/remote-accesses/' + remote_access.id)
}

export function getAllRemoteNodes(filter) {
    return ApiService.get('/config/remote-nodes?search=' + filter.search)
}

export function createNewRemoteNode(remote_node) {
    return ApiService.post('/config/remote-nodes', remote_node)
}

export function updateRemoteNode(remote_node) {
    return ApiService.put('/config/remote-nodes/' + remote_node.id, remote_node)
}

export function deleteRemoteNode(remote_node) {
    return ApiService.delete('/config/remote-nodes/' + remote_node.id)
}

export function connectRemoteNode(remote_node) {
    return ApiService.get('/config/remote-nodes/' + remote_node.id + '/connect')
}

export function getAllCollectorsNodes(filter) {
    return ApiService.get('/config/collectors-nodes?search=' + filter.search)
}

export function createNewCollectorsNode(node) {
    return ApiService.post('/config/collectors-nodes', node)
}

export function updateCollectorsNode(node) {
    return ApiService.put('/config/collectors-nodes/' + node.id, node)
}

export function deleteCollectorsNode(node) {
    return ApiService.delete('/config/collectors-nodes/' + node.id)
}

export function getAllOSINTSources(filter) {
    return ApiService.get('/config/osint-sources?search=' + filter.search)
}

export function createNewOSINTSource(source) {
    return ApiService.post('/config/osint-sources', source)
}

export function updateOSINTSource(source) {
    return ApiService.put('/config/osint-sources/' + source.id, source)
}

export function deleteOSINTSource(source) {
    return ApiService.delete('/config/osint-sources/' + source.id)
}

export function importOSINTSources(form_data) {
    return ApiService.upload('/config/import-osint-sources', form_data)
}

export function exportOSINTSources(data) {
    return ApiService.download('/config/export-osint-sources', data, 'osint_sources_export.json')
}

export function getAllOSINTSourceGroups(filter) {
    return ApiService.get('/config/osint-source-groups?search=' + filter.search)
}

export function createNewOSINTSourceGroup(group) {
    return ApiService.post('/config/osint-source-groups', group)
}

export function updateOSINTSourceGroup(group) {
    return ApiService.put('/config/osint-source-groups/' + group.id, group)
}

export function deleteOSINTSourceGroup(group) {
    return ApiService.delete('/config/osint-source-groups/' + group.id)
}

export function getAllPresentersNodes(filter) {
    return ApiService.get('/config/presenters-nodes?search=' + filter.search)
}

export function createNewPresentersNode(node) {
    return ApiService.post('/config/presenters-nodes', node)
}

export function updatePresentersNode(node) {
    return ApiService.put('/config/presenters-nodes/' + node.id, node)
}

export function deletePresentersNode(node) {
    return ApiService.delete('/config/presenters-nodes/' + node.id)
}

export function getAllPublishersNodes(filter) {
    return ApiService.get('/config/publishers-nodes?search=' + filter.search)
}

export function createNewPublishersNode(node) {
    return ApiService.post('/config/publishers-nodes', node)
}

export function updatePublishersNode(node) {
    return ApiService.put('/config/publishers-nodes/' + node.id, node)
}

export function deletePublishersNode(node) {
    return ApiService.delete('/config/publishers-nodes/' + node.id)
}

export function getAllPublisherPresets(filter) {
    return ApiService.get('/config/publishers-presets?search=' + filter.search)
}

export function createNewPublisherPreset(preset) {
    return ApiService.post('/config/publishers-presets', preset)
}

export function updatePublisherPreset(node) {
    return ApiService.put('/config/publishers-presets/' + node.id, node)
}

export function deletePublisherPreset(node) {
    return ApiService.delete('/config/publishers-presets/' + node.id)
}

export function getAllBotsNodes(filter) {
    return ApiService.get('/config/bots-nodes?search=' + filter.search)
}

export function createNewBotsNode(node) {
    return ApiService.post('/config/bots-nodes', node)
}

export function updateBotsNode(node) {
    return ApiService.put('/config/bots-nodes/' + node.id, node)
}

export function deleteBotsNode(node) {
    return ApiService.delete('/config/bots-nodes/' + node.id)
}

export function getAllBotPresets(filter) {
    return ApiService.get('/config/bots-presets?search=' + filter.search)
}

export function createNewBotPreset(preset) {
    return ApiService.post('/config/bots-presets', preset)
}

export function updateBotPreset(node) {
    return ApiService.put('/config/bots-presets/' + node.id, node)
}

export function deleteBotPreset(node) {
    return ApiService.delete('/config/bots-presets/' + node.id)
}