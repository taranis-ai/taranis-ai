import {
  getAllReportItems,
  getAllReportTypes,
  getReportItem,
  cloneReportItem,
  updateReportItem,
  deleteReportItem,
  addStoriesToReportItem
} from '@/api/analyze'

import { defineStore } from 'pinia'
import { useFilterStore } from './FilterStore'
import { useAssessStore } from './AssessStore'
import { i18n } from '@/i18n/i18n'
import { notifyFailure, notifySuccess } from '@/utils/helpers'
import { ref, computed } from 'vue'

const mapReportItem = (item, report_item_types) => {
  return {
    id: item.id,
    completed: item.completed,
    title: item.title,
    created: i18n.global.d(item.created, 'long'),
    type: report_item_types.find((type) => type.id === item.report_item_type_id)
      ?.title,
    stories: item.stories.length
  }
}

export const useAnalyzeStore = defineStore(
  'analyze',
  () => {
    const report_items = ref({ total_count: 0, items: [] })
    const report_item_types = ref({ total_count: 0, items: [] })
    const last_report = ref(null)
    const report_item_stories = ref({})

    const getReportItemsList = computed(() => {
      return report_items.value.items.map((item) => {
        return {
          title: item.title,
          value: item.id
        }
      })
    })

    const getReportItemsTableData = computed(() => {
      return report_items.value.items.map((item) =>
        mapReportItem(item, report_item_types.value.items)
      )
    })

    const getReportItemsByIDs = computed(() => (report_ids) => {
      const items = report_items.value.items.filter((item) =>
        report_ids.includes(item.id)
      )

      return items.map((item) =>
        mapReportItem(item, report_item_types.value.items)
      )
    })

    const getReportItemsByTypeIDs = computed(() => (report_type_ids) => {
      const items = report_items.value.items.filter((item) =>
        report_type_ids.includes(item.report_item_type_id)
      )

      return items.map((item) =>
        mapReportItem(item, report_item_types.value.items)
      )
    })

    async function loadReportItems() {
      const response = await getAllReportItems('')
      report_items.value = response.data
    }

    async function getReportyID(id) {
      let report = report_items.value.items.filter((item) => item.id === id)[0]
      if (!report) {
        const response = getReportItem(id)
        report = response.data
        report_items.value.items.push(report)
      }
      return report
    }

    async function updateReportItems() {
      const filterStore = useFilterStore()
      try {
        const response = await getAllReportItems(filterStore.reportFilterQuery)
        report_items.value = response.data
      } catch (error) {
        report_items.value = { total_count: 0, items: [] }
        notifyFailure(error)
      }
    }

    async function updateReportByID(report_item_id) {
      const response = await getReportItem(report_item_id)
      const updated_item = response.data
      let found = false

      report_items.value.items = report_items.value.items.map((item) => {
        if (item.id === report_item_id) {
          found = true
          return { ...item, ...updated_item }
        }
        return item
      })

      if (!found) {
        report_items.value.items.push(updated_item)
      }
    }

    async function patchReportItem(report_item_id, data) {
      try {
        const response = await updateReportItem(report_item_id, data)
        notifySuccess(response.data.message)
      } catch (error) {
        notifyFailure(error)
      }
      report_items.value.items = report_items.value.items.map((item) => {
        if (item.id === report_item_id) {
          return { ...item, ...data }
        }
        return item
      })
    }

    async function cloneReport(report_item_id) {
      try {
        const response = await cloneReportItem(report_item_id)
        await updateReportItems()
        notifySuccess(response.data.message)
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadReportTypes(data) {
      const response = await getAllReportTypes(data)
      report_item_types.value = response.data
    }

    function addStoriesToReport(report_item_id, stories) {
      addStoriesToReportItem(report_item_id, stories)
      const report_item = report_items.value.items.find(
        (item) => item.id === report_item_id
      )
      if (report_item) {
        report_item.stories = stories
      }
      last_report.value = report_item_id
      const assessStore = useAssessStore()
      for (const story of stories) {
        assessStore.storyAddedToReport(story)
      }
    }

    function sseReportItemUpdate(data) {
      console.debug('Triggerd report item update: ' + data)
      updateReportByID(data.id)
    }

    async function removeReport(report_item) {
      const report_item_id = report_item.id || report_item
      try {
        const response = await deleteReportItem(report_item_id)
        report_items.value.items = report_items.value.items.filter(
          (item) => item.id !== report_item_id
        )
        notifySuccess(response.data.message)
      } catch (error) {
        notifyFailure(error)
      }
    }

    function reset() {
      report_items.value = { total_count: 0, items: [] }
      report_item_types.value = { total_count: 0, items: [] }
      last_report.value = null
    }

    return {
      report_items,
      report_item_types,
      last_report,
      report_item_stories,
      getReportItemsList,
      getReportItemsTableData,
      getReportItemsByIDs,
      getReportItemsByTypeIDs,
      getReportyID,
      patchReportItem,
      loadReportItems,
      updateReportItems,
      updateReportByID,
      cloneReport,
      loadReportTypes,
      removeReport,
      addStoriesToReport,
      sseReportItemUpdate,
      reset
    }
  },
  {
    persist: true
  }
)
