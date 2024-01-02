import { getAllReportItems, getAllReportTypes } from '@/api/analyze'

import { defineStore } from 'pinia'
import { useFilterStore } from './FilterStore'
import { useI18n } from 'vue-i18n'

const mapReportItem = (item, d, report_item_types) => {
  return {
    id: item.id,
    completed: item.completed,
    title: item.title,
    created: d(item.created, 'long'),
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
      const { d } = useI18n()

      return this.report_items.items.map((item) =>
        mapReportItem(item, d, this.report_item_types.items)
      )
    },
    getReportItemsByIDs: (state) => (report_item_ids) => {
      const { d } = useI18n()

      const items =
        report_item_ids.length > 0
          ? state.report_items.items.filter((item) =>
              report_item_ids.includes(item.report_item_type_id)
            )
          : state.report_items.items

      return items.map((item) =>
        mapReportItem(item, d, state.report_item_types.items)
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

    async loadReportTypes(data) {
      const response = await getAllReportTypes(data)
      this.report_item_types = response.data
    },

    addSelectionReport(selected_item) {
      this.selection_report.push(selected_item)
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
