import {
  getAllACLEntries,
  getAllAttributes,
  getAllBots,
  getAllCollectors,
  getAllExternalPermissions,
  getAllExternalUsers,
  getAllOrganizations,
  getAllOSINTSourceGroups,
  getAllOSINTSources,
  getAllPermissions,
  getAllProductTypes,
  getAllPublisherPresets,
  getAllPresenters,
  getAllPublishers,
  getAllRemoteAccesses,
  getAllRemoteNodes,
  getAllReportTypes,
  getAllRoles,
  getAllUsers,
  getAllNodes,
  getAllWordLists,
  getAllParameters
} from '@/api/config'
import { getAllUserProductTypes, getAllUserWordLists } from '@/api/user'

const state = {
  acls: { total_count: 0, items: [] },
  attributes: { total_count: 0, items: [] },
  bots: { total_count: 0, items: [] },
  collectors: { total_count: 0, items: [] },
  nodes: { total_count: 0, items: [] },
  organizations: { total_count: 0, items: [] },
  osint_sources: { total_count: 0, items: [] },
  osint_source_groups: { total_count: 0, items: [] },
  parameters: { total_count: 0, items: [] },
  permissions: { total_count: 0, items: [] },
  product_types: { total_count: 0, items: [] },
  publisher_presets: { total_count: 0, items: [] },
  presenters: { total_count: 0, items: [] },
  publishers: { total_count: 0, items: [] },
  remote_access: { total_count: 0, items: [] },
  remote_nodes: { total_count: 0, items: [] },
  report_item_types_config: { total_count: 0, items: [] },
  roles: { total_count: 0, items: [] },
  users: { total_count: 0, items: [] },
  word_lists: { total_count: 0, items: [] }
}

const actions = {

  loadAttributes (context, data) {
    return getAllAttributes(data)
      .then(response => {
        context.commit('setAttributes', response.data)
      })
  },

  loadReportTypesConfig (context, data) {
    return getAllReportTypes(data)
      .then(response => {
        context.commit('setReportItemTypesConfig', response.data)
      })
  },

  loadProductTypes (context, data) {
    return getAllProductTypes(data)
      .then(response => {
        context.commit('setProductTypes', response.data)
      })
  },

  loadUserProductTypes (context, data) {
    return getAllUserProductTypes(data)
      .then(response => {
        context.commit('setProductTypes', response.data)
      })
  },

  loadPermissions (context, data) {
    return getAllPermissions(data)
      .then(response => {
        context.commit('setPermissions', response.data)
      })
  },

  loadExternalPermissions (context, data) {
    return getAllExternalPermissions(data)
      .then(response => {
        context.commit('setPermissions', response.data)
      })
  },

  loadRoles (context, data) {
    return getAllRoles(data)
      .then(response => {
        context.commit('setRoles', response.data)
      })
  },

  loadACLEntries (context, data) {
    return getAllACLEntries(data)
      .then(response => {
        context.commit('setACLEntries', response.data)
      })
  },

  loadOrganizations (context, data) {
    return getAllOrganizations(data)
      .then(response => {
        context.commit('setOrganizations', response.data)
      })
  },

  loadUsers (context, data) {
    return getAllUsers(data)
      .then(response => {
        context.commit('setUsers', response.data)
      })
  },

  loadExternalUsers (context, data) {
    return getAllExternalUsers(data)
      .then(response => {
        context.commit('setUsers', response.data)
      })
  },

  loadWordLists (context, data) {
    return getAllWordLists(data)
      .then(response => {
        context.commit('setWordLists', response.data)
      })
  },

  loadUserWordLists (context, data) {
    return getAllUserWordLists(data)
      .then(response => {
        context.commit('setWordLists', response.data)
      })
  },

  loadRemoteAccesses (context, data) {
    return getAllRemoteAccesses(data)
      .then(response => {
        context.commit('setRemoteAccesses', response.data)
      })
  },

  loadRemoteNodes (context, data) {
    return getAllRemoteNodes(data)
      .then(response => {
        context.commit('setRemoteNodes', response.data)
      })
  },

  loadNodes (context, data) {
    return getAllNodes(data)
      .then(response => {
        context.commit('setNodes', response.data)
      })
  },

  loadOSINTSources (context, data) {
    return getAllOSINTSources(data)
      .then(response => {
        context.commit('setOSINTSources', response.data)
      })
  },

  loadCollectors (context, data) {
    return getAllCollectors(data)
      .then(response => {
        context.commit('setCollectors', response.data)
      })
  },

  loadBots (context, data) {
    return getAllBots(data)
      .then(response => {
        context.commit('setBots', response.data)
      })
  },

  loadPresenters(context, data) {
    return getAllPresenters(data)
      .then(response => {
        context.commit('setPresenters', response.data)
      })
  },

  loadPublishers(context, data) {
    return getAllPublishers(data)
      .then(response => {
        context.commit('setPublishers', response.data)
      })
  },

  loadOSINTSourceGroups (context, filter) {
    return getAllOSINTSourceGroups(filter)
      .then(response => {
        context.commit('setOSINTSourceGroups', response.data)
      })
  },

  loadPublisherPresets (context, data) {
    return getAllPublisherPresets(data)
      .then(response => {
        context.commit('setPublisherPresets', response.data)
      })
  },

  loadParameters (context, data) {
    return getAllParameters(data)
      .then(response => {
        context.commit('setParameters', response.data)
      })
  }
}

const mutations = {
  setAttributes (state, attributes) {
    state.attributes = attributes
  },

  setReportItemTypesConfig (state, report_item_types_config) {
    state.report_item_types_config = report_item_types_config
  },

  setProductTypes (state, product_types) {
    state.product_types = product_types
  },

  setPermissions (state, permissions) {
    state.permissions = permissions
  },

  setRoles (state, roles) {
    state.roles = roles
  },

  setACLEntries (state, acls) {
    state.acls = acls
  },

  setOrganizations (state, organizations) {
    state.organizations = organizations
  },

  setUsers (state, users) {
    state.users = users
  },

  setWordLists (state, word_lists) {
    state.word_lists = word_lists
  },

  setRemoteAccesses (state, remote_access) {
    state.remote_access = remote_access
  },

  setRemoteNodes (state, remote_nodes) {
    state.remote_nodes = remote_nodes
  },

  setNodes (state, nodes) {
    state.nodes = nodes
  },

  setCollectors (state, collectors) {
    state.collectors = collectors
  },

  setBots (state, bots) {
    state.bots = bots
  },

  setPresenters (state, presenters) {
    state.presenters = presenters
  },

  setPublishers (state, publishers) {
    state.publishers = publishers
  },

  setOSINTSources (state, osint_sources) {
    state.osint_sources = osint_sources
  },

  setOSINTSourceGroups (state, osint_source_groups) {
    state.osint_source_groups = osint_source_groups
  },

  setPublisherPresets (state, publisher_presets) {
    state.publisher_presets = publisher_presets
  },

  setParameters (state, parameters) {
    state.parameters = parameters
  }
}

const getters = {
  getAttributes (state) {
    return state.attributes
  },

  getReportTypesConfig (state) {
    return state.report_item_types_config
  },

  getProductTypes (state) {
    return state.product_types
  },

  getPermissions (state) {
    return state.permissions
  },

  getRoles (state) {
    return state.roles
  },

  getACLEntries (state) {
    return state.acls
  },

  getOrganizations (state) {
    return state.organizations
  },

  getUsers (state) {
    return state.users
  },

  getUserByID: (state, getters) => (user_id) => {
    for (const user of state.users.items) {
      if (user.id === user_id) {
        return user
      }
    }
    return null
  },

  getWordLists (state) {
    return state.word_lists
  },

  getRemoteAccesses (state) {
    return state.remote_access
  },

  getRemoteNodes (state) {
    return state.remote_nodes
  },

  getCollectorsNodes (state) {
    return state.nodes.items.map(function (item) {
      if (item.type === 'Collector') {
        return item
      }
    })
  },

  getNodes (state) {
    return state.nodes
  },

  getCollectors (state) {
    return state.collectors
  },

  getBots (state) {
    return state.bots
  },

  getOSINTSources (state) {
    return state.osint_sources
  },

  getOSINTSourceGroups (state) {
    return state.osint_source_groups
  },

  getPresentersNodes (state) {
    return state.nodes.items.map(function (item) {
      if (item.type === 'Presenter') {
        return item
      }
    })
  },

  getPublishersNodes (state) {
    return state.nodes.items.map(function (item) {
      if (item.type === 'Publisher') {
        return item
      }
    })
  },

  getBotsNodes (state) {
    return state.nodes.items.map(function (item) {
      if (item.type === 'Bot') {
        return item
      }
    })
  },

  getPublisherPresets (state) {
    return state.publisher_presets
  },

  getParameters (state) {
    return state.parameters
  },
  getPresenters (state) {
    return state.presenters
  },
  getPublishers (state) {
    return state.publishers
  }
}

export const config = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
