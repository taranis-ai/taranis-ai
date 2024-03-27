import { defineStore } from 'pinia'
import { notifyFailure, getMessageFromError } from '@/utils/helpers'
import {
  getAllACLEntries,
  getAllAttributes,
  getAllBots,
  getAllOrganizations,
  getAllOSINTSourceGroups,
  getAllOSINTSources,
  getAllPermissions,
  getAllProductTypes,
  getAllPublisher,
  getAllReportTypes,
  getAllRoles,
  getAllUsers,
  getAllWordLists,
  getAllParameters,
  getAllSchedule,
  getAllTemplates,
  getAllWorkers,
  getAllWorkerTypes,
  getQueueStatus,
  getQueueTasks
} from '@/api/config'

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
    publisher: { total_count: 0, items: [] },
    report_item_types: { total_count: 0, items: [] },
    roles: { total_count: 0, items: [] },
    users: { total_count: 0, items: [] },
    templates: { total_count: 0, items: [] },
    word_lists: { total_count: 0, items: [] },
    schedule: [],
    workers: [],
    worker_types: { total_count: 0, items: [] },
    queue_status: {},
    queue_tasks: []
  }),
  getters: {
    getUserByID: (state) => (user_id) => {
      return state.users.items.find((user) => user.id === user_id) || null
    },
    getOSINTSourceNameByID: (state) => (osint_source_id) => {
      return (
        state.osint_sources.items.find(
          (osint_source) => osint_source.id === osint_source_id
        ).name || osint_source_id
      )
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
    },
    collector_word_lists: (state) => {
      return state.word_lists.items.filter((word_list) =>
        word_list.usage.some((usage) => usage.includes('COLLECTOR'))
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
          notifyFailure(error)
        })
    },
    loadBots(data) {
      return getAllBots(data)
        .then((response) => {
          this.bots = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadReportTypes(data) {
      return getAllReportTypes(data)
        .then((response) => {
          this.report_item_types = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadProductTypes(data) {
      return getAllProductTypes(data)
        .then((response) => {
          this.product_types = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadPermissions(data) {
      return getAllPermissions(data)
        .then((response) => {
          this.permissions = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadRoles(data) {
      return getAllRoles(data)
        .then((response) => {
          this.roles = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadACLEntries(data) {
      return getAllACLEntries(data)
        .then((response) => {
          this.acls = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadOrganizations(data) {
      return getAllOrganizations(data)
        .then((response) => {
          this.organizations = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadUsers(data) {
      return getAllUsers(data)
        .then((response) => {
          this.users = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadWordLists(data) {
      return getAllWordLists(data)
        .then((response) => {
          this.word_lists = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadOSINTSources(data) {
      return getAllOSINTSources(data)
        .then((response) => {
          this.osint_sources = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadWorkerTypes(data) {
      return getAllWorkerTypes(data)
        .then((response) => {
          this.worker_types = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadOSINTSourceGroups(filter) {
      return getAllOSINTSourceGroups(filter)
        .then((response) => {
          this.osint_source_groups = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadPublisher(data) {
      return getAllPublisher(data)
        .then((response) => {
          this.publisher = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    loadParameters(data) {
      return getAllParameters(data)
        .then((response) => {
          this.parameters = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    async loadTemplates(data) {
      return getAllTemplates(data)
        .then((response) => {
          this.templates = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    async loadSchedule(data) {
      return getAllSchedule(data)
        .then((response) => {
          this.schedule = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    async loadQueueStatus(data) {
      return getQueueStatus(data)
        .then((response) => {
          this.queue_status = response.data
        })
        .catch((error) => {
          const error_message = getMessageFromError(error)
          this.queue_status = error_message
          notifyFailure(error_message)
        })
    },
    async loadQueueTasks(data) {
      return getQueueTasks(data)
        .then((response) => {
          this.queue_tasks = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    },
    async loadWorkers(data) {
      return getAllWorkers(data)
        .then((response) => {
          this.workers = response.data
        })
        .catch((error) => {
          notifyFailure(error)
        })
    }
  },
  persist: true
})
