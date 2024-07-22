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
import { ref, computed } from 'vue'

export const useConfigStore = defineStore(
  'config',
  () => {
    const acls = ref({ total_count: 0, items: [] })
    const attributes = ref({ total_count: 0, items: [] })
    const bots = ref({ total_count: 0, items: [] })
    const organizations = ref({ total_count: 0, items: [] })
    const osint_sources = ref({ total_count: 0, items: [] })
    const osint_source_groups = ref({ total_count: 0, items: [] })
    const parameters = ref([])
    const permissions = ref({ total_count: 0, items: [] })
    const product_types = ref({ total_count: 0, items: [] })
    const publisher = ref({ total_count: 0, items: [] })
    const report_item_types = ref({ total_count: 0, items: [] })
    const roles = ref({ total_count: 0, items: [] })
    const users = ref({ total_count: 0, items: [] })
    const templates = ref({ total_count: 0, items: [] })
    const word_lists = ref({ total_count: 0, items: [] })
    const schedule = ref([])
    const workers = ref([])
    const worker_types = ref({ total_count: 0, items: [] })
    const queue_status = ref({})
    const queue_tasks = ref([])

    const getUserByID = computed(() => (user_id) => {
      return users.value.items.find((user) => user.id === user_id) || null
    })

    const getOSINTSourceNameByID = computed(() => (osint_source_id) => {
      return (
        osint_sources.value.items.find(
          (osint_source) => osint_source.id === osint_source_id
        )?.name || osint_source_id
      )
    })

    const collector_types = computed(() => {
      return worker_types.value.items.filter((worker_type) =>
        worker_type.type.endsWith('collector')
      )
    })

    const bot_types = computed(() => {
      return worker_types.value.items.filter((worker_type) =>
        worker_type.type.endsWith('bot')
      )
    })

    const publisher_types = computed(() => {
      return worker_types.value.items.filter((worker_type) =>
        worker_type.type.endsWith('publisher')
      )
    })

    const presenter_types = computed(() => {
      return worker_types.value.items.filter((worker_type) =>
        worker_type.type.endsWith('presenter')
      )
    })

    const collector_word_lists = computed(() => {
      return word_lists.value.items.filter((word_list) =>
        word_list.usage.some((usage) => usage.includes('COLLECTOR'))
      )
    })

    const enhanced_schedule = computed(() => {
      return schedule.value.map((item) => {
        if (item.task === 'collector_task') {
          item.args = getOSINTSourceNameByID.value(item.args)
        }
        return item
      })
    })

    async function loadAttributes(data) {
      try {
        const response = await getAllAttributes(data)
        attributes.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadBots(data) {
      try {
        const response = await getAllBots(data)
        bots.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadReportTypes(data) {
      try {
        const response = await getAllReportTypes(data)
        report_item_types.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadProductTypes(data) {
      try {
        const response = await getAllProductTypes(data)
        product_types.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadPermissions(data) {
      try {
        const response = await getAllPermissions(data)
        permissions.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadRoles(data) {
      try {
        const response = await getAllRoles(data)
        roles.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadACLEntries(data) {
      try {
        const response = await getAllACLEntries(data)
        acls.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadOrganizations(data) {
      try {
        const response = await getAllOrganizations(data)
        organizations.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadUsers(data) {
      try {
        const response = await getAllUsers(data)
        users.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadWordLists(data) {
      try {
        const response = await getAllWordLists(data)
        word_lists.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadOSINTSources(data) {
      try {
        const response = await getAllOSINTSources(data)
        osint_sources.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadWorkerTypes(data) {
      try {
        const response = await getAllWorkerTypes(data)
        worker_types.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadOSINTSourceGroups(filter) {
      try {
        const response = await getAllOSINTSourceGroups(filter)
        osint_source_groups.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadPublisher(data) {
      try {
        const response = await getAllPublisher(data)
        publisher.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadParameters(data) {
      try {
        const response = await getAllParameters(data)
        parameters.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadTemplates(data) {
      try {
        const response = await getAllTemplates(data)
        templates.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadSchedule(data) {
      try {
        const response = await getAllSchedule(data)
        schedule.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadQueueStatus(data) {
      try {
        const response = await getQueueStatus(data)
        queue_status.value = response.data
      } catch (error) {
        const error_message = getMessageFromError(error)
        queue_status.value = error_message
        notifyFailure(error_message)
      }
    }

    async function loadQueueTasks(data) {
      try {
        const response = await getQueueTasks(data)
        queue_tasks.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadWorkers(data) {
      try {
        const response = await getAllWorkers(data)
        workers.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    function reset() {
      acls.value = { total_count: 0, items: [] }
      attributes.value = { total_count: 0, items: [] }
      bots.value = { total_count: 0, items: [] }
      organizations.value = []
      osint_sources.value = { total_count: 0, items: [] }
      osint_source_groups.value = { total_count: 0, items: [] }
      parameters.value = []
      permissions.value = { total_count: 0, items: [] }
      product_types.value = { total_count: 0, items: [] }
      publisher.value = { total_count: 0, items: [] }
      report_item_types.value = { total_count: 0, items: [] }
      roles.value = { total_count: 0, items: [] }
      users.value = { total_count: 0, items: [] }
      templates.value = { total_count: 0, items: [] }
      word_lists.value = { total_count: 0, items: [] }
      schedule.value = []
      workers.value = []
      worker_types.value = { total_count: 0, items: [] }
      queue_status.value = {}
      queue_tasks.value = []
    }

    return {
      acls,
      attributes,
      bots,
      organizations,
      osint_sources,
      osint_source_groups,
      parameters,
      permissions,
      product_types,
      publisher,
      report_item_types,
      roles,
      users,
      templates,
      word_lists,
      schedule,
      workers,
      worker_types,
      queue_status,
      queue_tasks,
      getUserByID,
      getOSINTSourceNameByID,
      collector_types,
      bot_types,
      publisher_types,
      presenter_types,
      collector_word_lists,
      enhanced_schedule,
      loadAttributes,
      loadBots,
      loadReportTypes,
      loadProductTypes,
      loadPermissions,
      loadRoles,
      loadACLEntries,
      loadOrganizations,
      loadUsers,
      loadWordLists,
      loadOSINTSources,
      loadWorkerTypes,
      loadOSINTSourceGroups,
      loadPublisher,
      loadParameters,
      loadTemplates,
      loadSchedule,
      loadQueueStatus,
      loadQueueTasks,
      loadWorkers,
      reset
    }
  },
  {
    persist: true
  }
)
