import {
  getAllReportItems,
  getAllReportTypes,
  getAllReportItemGroups
} from '@/api/analyze'

import { defineStore } from 'pinia'
import { useFilterStore } from './FilterStore'

export const useAnalyzeStore = defineStore('analyze', {
  state: () => ({
    report_items: { total_count: 0, items: [] },
    report_item_types: { total_count: 0, items: [] },
    selection_report: [],
    report_item_groups: [],
    current_report_item_group_id: null
  }),
  actions: {
    async loadReportItemGroups() {
      const response = await getAllReportItemGroups()
      this.report_item_groups = response.data
    },

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
