import {
  getAllReportItems,
  getAllReportTypes,
  getReportItem,
  cloneReportItem,
  addAggregatesToReportItem
} from '@/api/analyze'

import { defineStore } from 'pinia'
import { useFilterStore } from './FilterStore'
import { useAssessStore } from './AssessStore'
import { i18n } from '@/i18n/i18n'
import { notifyFailure, notifySuccess } from '@/utils/helpers'

const mapReportItem = (item, report_item_types) => {
  return {
    id: item.id,
    completed: item.completed,
    title: item.title,
    created: i18n.global.d(item.created, 'long'),
    type: report_item_types.find((type) => type.id === item.report_item_type_id)
      ?.title,
    stories: item.stories
  }
}

export const useAnalyzeStore = defineStore('analyze', {
  state: () => ({
    report_items: { total_count: 0, items: [] },
    report_item_types: { total_count: 0, items: [] },
    selection_report: [],
    current_report_item_group_id: null
  }),
  getters: {
    getReportItemsList() {
      return this.report_items.items.map((item) => {
        return {
          title: item.title,
          value: item.id
        }
      })
    },
    getReportItemsTableData() {
      return this.report_items.items.map((item) =>
        mapReportItem(item, this.report_item_types.items)
      )
    },
    getReportItemsByIDs: (state) => (report_item_ids) => {
      const items = state.report_items.items.filter((item) =>
        report_item_ids.includes(item.report_item_type_id)
      )

      return items.map((item) =>
        mapReportItem(item, state.report_item_types.items)
      )
    }
  },
  actions: {
    async loadReportItems(data) {
      const response = await getAllReportItems(data)
      this.report_items = response.data
    },

    async updateReportItems() {
      const filter = useFilterStore()
      const response = await getAllReportItems(filter.reportFilter)
      this.report_items = response.data
    },

    async updateReportByID(report_item_id) {
      const response = await getReportItem(report_item_id)
      const updated_item = response.data
      let found = false

      this.report_items.items = this.report_items.items.map((item) => {
        if (item.id === report_item_id) {
          found = true
          return { ...item, ...updated_item }
        }
        return item
      })

      if (!found) {
        this.report_items.items.push(updated_item)
      }
    },

    async cloneReport(report_item_id) {
      try {
        const response = await cloneReportItem(report_item_id)
        await this.loadReportItems()
        notifySuccess(response.data.message)
      } catch (error) {
        notifyFailure(error)
      }
    },

    async loadReportTypes(data) {
      const response = await getAllReportTypes(data)
      this.report_item_types = response.data
    },

    addStoriesToReport(report_item_id, stories) {
      addAggregatesToReportItem(report_item_id, stories)
      const report_item = this.report_items.items.find(
        (item) => item.id === report_item_id
      )
      if (report_item) {
        report_item.stories = stories
      }
      const assessStore = useAssessStore()
      for (const story of stories) {
        assessStore.storyAddedToReport(story)
      }
    },

    addSelectionReport(selected_item) {
      this.selection_report.push(selected_item)
    },

    sseReportItemUpdate(data) {
      console.debug('Triggerd report item update: ' + data)
      this.updateReportByID(data.id)
    },

    removeSelectionReport(selectedItem) {
      for (let i = 0; i < this.selection_report.length; i++) {
        if (this.selection_report[i].id === selectedItem.id) {
          this.selection_report.splice(i, 1)
          break
        }
      }
    }
  }
})
