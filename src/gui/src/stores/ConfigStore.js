import { defineStore } from 'pinia'
import { notifyFailure } from '@/utils/helpers'
import {
  getAllACLEntries,
  getAllAttributes,
  getAllBots,
  getAllCollectors,
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
  getAllParameters,
  getAllSchedule,
  getAllWorkers
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
    word_lists: { total_count: 0, items: [] },
    schedule: [],
    workers: []
  }),
  getters: {
    getUserByID: (state) => (user_id) => {
      return state.users.items.find((user) => user.id === user_id) || null
    }
  },
  actions: {
    loadAttributes(data) {
      return getAllAttributes(data)
        .then((response) => {
          this.attributes = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadReportTypesConfig(data) {
      return getAllReportTypes(data)
        .then((response) => {
          this.report_item_types_config = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadProductTypes(data) {
      return getAllProductTypes(data)
        .then((response) => {
          this.product_types = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadUserProductTypes(data) {
      return getAllUserProductTypes(data)
        .then((response) => {
          this.product_types = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadPermissions(data) {
      return getAllPermissions(data)
        .then((response) => {
          this.permissions = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadRoles(data) {
      return getAllRoles(data)
        .then((response) => {
          this.roles = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadACLEntries(data) {
      return getAllACLEntries(data)
        .then((response) => {
          this.acls = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadOrganizations(data) {
      return getAllOrganizations(data)
        .then((response) => {
          this.organizations = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadUsers(data) {
      return getAllUsers(data)
        .then((response) => {
          this.users = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadExternalUsers(data) {
      return getAllExternalUsers(data)
        .then((response) => {
          this.users = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadWordLists(data) {
      return getAllWordLists(data)
        .then((response) => {
          this.word_lists = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadRemoteAccesses(data) {
      return getAllRemoteAccesses(data)
        .then((response) => {
          this.remote_access = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadRemoteNodes(data) {
      return getAllRemoteNodes(data)
        .then((response) => {
          this.remote_nodes = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadNodes(data) {
      return getAllNodes(data)
        .then((response) => {
          this.nodes = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadOSINTSources(data) {
      return getAllOSINTSources(data)
        .then((response) => {
          this.osint_sources = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadCollectors(data) {
      return getAllCollectors(data)
        .then((response) => {
          this.collectors = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadBots(data) {
      return getAllBots(data)
        .then((response) => {
          this.bots = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadPresenters(data) {
      return getAllPresenters(data)
        .then((response) => {
          this.presenters = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadPublishers(data) {
      return getAllPublishers(data)
        .then((response) => {
          this.publishers = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadOSINTSourceGroups(filter) {
      return getAllOSINTSourceGroups(filter)
        .then((response) => {
          this.osint_source_groups = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadPublisherPresets(data) {
      return getAllPublisherPresets(data)
        .then((response) => {
          this.publisher_presets = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadParameters(data) {
      return getAllParameters(data)
        .then((response) => {
          this.parameters = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadSchedule(data) {
      return getAllSchedule(data)
        .then((response) => {
          this.schedule = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    },
    loadWorkers(data) {
      return getAllWorkers(data)
        .then((response) => {
          this.workers = response.data
        })
        .catch((error) => {
          notifyFailure(error.message)
        })
    }
  }
})
