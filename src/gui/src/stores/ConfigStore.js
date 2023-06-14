import { defineStore } from 'pinia'
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
import { getAllUserProductTypes } from '@/api/user'

export const useConfigStore = defineStore('config', {
  state: () => ({
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
  }),
  getters: {
    getUserByID: (state) => (user_id) => {
      return state.users.items.find((user) => user.id === user_id) || null
    },
    getCollectorsNodes() {
      return this.nodes.items.map(function (item) {
        if (item.type === 'Collector') {
          return item
        }
      })
    },
    getPresentersNodes() {
      return this.nodes.items.map(function (item) {
        if (item.type === 'Presenter') {
          return item
        }
      })
    },
    getPublishersNodes() {
      return this.nodes.items.map(function (item) {
        if (item.type === 'Publisher') {
          return item
        }
      })
    },
    getBotsNodes() {
      return this.nodes.items.map(function (item) {
        if (item.type === 'Bot') {
          return item
        }
      })
    }
  },
  actions: {
    loadAttributes(data) {
      return getAllAttributes(data).then((response) => {
        this.attributes = response.data
      })
    },
    loadReportTypesConfig(data) {
      return getAllReportTypes(data).then((response) => {
        this.report_item_types_config = response.data
      })
    },
    loadProductTypes(data) {
      return getAllProductTypes(data).then((response) => {
        this.product_types = response.data
      })
    },
    loadUserProductTypes(data) {
      return getAllUserProductTypes(data).then((response) => {
        this.product_types = response.data
      })
    },
    loadPermissions(data) {
      return getAllPermissions(data).then((response) => {
        this.permissions = response.data
      })
    },
    loadExternalPermissions(data) {
      return getAllExternalPermissions(data).then((response) => {
        this.permissions = response.data
      })
    },
    loadRoles(data) {
      return getAllRoles(data).then((response) => {
        this.roles = response.data
      })
    },
    loadACLEntries(data) {
      return getAllACLEntries(data).then((response) => {
        this.acls = response.data
      })
    },
    loadOrganizations(data) {
      return getAllOrganizations(data).then((response) => {
        this.organizations = response.data
      })
    },
    loadUsers(data) {
      return getAllUsers(data).then((response) => {
        this.users = response.data
      })
    },
    loadExternalUsers(data) {
      return getAllExternalUsers(data).then((response) => {
        this.users = response.data
      })
    },
    loadWordLists(data) {
      return getAllWordLists(data).then((response) => {
        this.word_lists = response.data
      })
    },
    loadRemoteAccesses(data) {
      return getAllRemoteAccesses(data).then((response) => {
        this.remote_access = response.data
      })
    },
    loadRemoteNodes(data) {
      return getAllRemoteNodes(data).then((response) => {
        this.remote_nodes = response.data
      })
    },
    loadNodes(data) {
      return getAllNodes(data).then((response) => {
        this.nodes = response.data
      })
    },
    loadOSINTSources(data) {
      return getAllOSINTSources(data).then((response) => {
        this.osint_sources = response.data
      })
    },
    loadCollectors(data) {
      return getAllCollectors(data).then((response) => {
        this.collectors = response.data
      })
    },
    loadBots(data) {
      return getAllBots(data).then((response) => {
        this.bots = response.data
      })
    },
    loadPresenters(data) {
      return getAllPresenters(data).then((response) => {
        this.presenters = response.data
      })
    },
    loadPublishers(data) {
      return getAllPublishers(data).then((response) => {
        this.publishers = response.data
      })
    },
    loadOSINTSourceGroups(filter) {
      return getAllOSINTSourceGroups(filter).then((response) => {
        this.osint_source_groups = response.data
      })
    },
    loadPublisherPresets(data) {
      return getAllPublisherPresets(data).then((response) => {
        this.publisher_presets = response.data
      })
    },
    loadParameters(data) {
      return getAllParameters(data).then((response) => {
        this.parameters = response.data
      })
    }
  }
})
