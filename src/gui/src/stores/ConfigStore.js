import { defineStore } from 'pinia'
import {
  notifyFailure,
  parseWordListEntries,
  getMessageFromError
} from '@/utils/helpers'
import {
  getAllACLEntries,
  getAllAttributes,
  getAllBots,
  getAllExternalUsers,
  getAllOrganizations,
  getAllOSINTSourceGroups,
  getAllOSINTSources,
  getAllPermissions,
  getAllProductTypes,
  getAllPublisherPresets,
  getAllReportTypes,
  getAllRoles,
  getAllUsers,
  getAllWordLists,
  getAllParameters,
  getAllSchedule,
  getAllWorkers,
  getAllWorkerTypes,
  getQueueStatus
} from '@/api/config'
import { getAllUserProductTypes } from '@/api/user'

export const useConfigStore = defineStore('config', {
  state: () => ({
    acls: { total_count: 0, items: [] },
    attributes: { total_count: 0, items: [] },
    bots: { total_count: 0, items: [] },
    organizations: { total_count: 0, items: [] },
    osint_sources: { total_count: 0, items: [] },
    osint_source_groups: { total_count: 0, items: [] },
    parameters: [],
    permissions: { total_count: 0, items: [] },
    product_types: { total_count: 0, items: [] },
    publisher_presets: { total_count: 0, items: [] },
    report_item_types: { total_count: 0, items: [] },
    roles: { total_count: 0, items: [] },
    users: { total_count: 0, items: [] },
    word_lists: { total_count: 0, items: [] },
    schedule: [],
    workers: [],
    worker_types: { total_count: 0, items: [] },
    queue_status: {}
  }),
  getters: {
    getUserByID: (state) => (user_id) => {
      return state.users.items.find((user) => user.id === user_id) || null
    },
    collector_types: (state) => {
      return state.worker_types.items.filter((worker_type) =>
        worker_type.type.endsWith('collector')
      )
    },
    bot_types: (state) => {
      return state.worker_types.items.filter((worker_type) =>
        worker_type.type.endsWith('bot')
      )
    },
    publisher_types: (state) => {
      return state.worker_types.items.filter((worker_type) =>
        worker_type.type.endsWith('publisher')
      )
    },
    presenter_types: (state) => {
      return state.worker_types.items.filter((worker_type) =>
        worker_type.type.endsWith('presenter')
      )
    }
  },
  actions: {
    loadAttributes(data) {
      return getAllAttributes(data)
        .then((response) => {
          this.attributes = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadBots(data) {
      return getAllBots(data)
        .then((response) => {
          this.bots = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadReportTypesConfig(data) {
      return getAllReportTypes(data)
        .then((response) => {
          this.report_item_types = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadProductTypes(data) {
      return getAllProductTypes(data)
        .then((response) => {
          this.product_types = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadUserProductTypes(data) {
      return getAllUserProductTypes(data)
        .then((response) => {
          this.product_types = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadPermissions(data) {
      return getAllPermissions(data)
        .then((response) => {
          this.permissions = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadRoles(data) {
      return getAllRoles(data)
        .then((response) => {
          this.roles = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadACLEntries(data) {
      return getAllACLEntries(data)
        .then((response) => {
          this.acls = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadOrganizations(data) {
      return getAllOrganizations(data)
        .then((response) => {
          this.organizations = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadUsers(data) {
      return getAllUsers(data)
        .then((response) => {
          this.users = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadExternalUsers(data) {
      return getAllExternalUsers(data)
        .then((response) => {
          this.users = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadWordLists(data) {
      return getAllWordLists(data)
        .then((response) => {
          this.word_lists = response.data
          this.word_lists.items.forEach((word_list) => {
            word_list.entries = parseWordListEntries(word_list.entries)
          })
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadOSINTSources(data) {
      return getAllOSINTSources(data)
        .then((response) => {
          this.osint_sources = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadWorkerTypes(data) {
      return getAllWorkerTypes(data)
        .then((response) => {
          this.worker_types = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadOSINTSourceGroups(filter) {
      return getAllOSINTSourceGroups(filter)
        .then((response) => {
          this.osint_source_groups = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadPublisherPresets(data) {
      return getAllPublisherPresets(data)
        .then((response) => {
          this.publisher_presets = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    loadParameters(data) {
      return getAllParameters(data)
        .then((response) => {
          this.parameters = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    async loadSchedule(data) {
      return getAllSchedule(data)
        .then((response) => {
          this.schedule = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    async loadQueueStatus(data) {
      return getQueueStatus(data)
        .then((response) => {
          this.queue_status = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    },
    async loadWorkers(data) {
      return getAllWorkers(data)
        .then((response) => {
          this.workers = response.data
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    }
  }
})
