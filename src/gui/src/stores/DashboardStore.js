import { defineStore } from 'pinia'
import {
  getDashboardData,
  getTrendingClusters,
  getCluster
} from '@/api/dashboard'
import { notifyFailure } from '@/utils/helpers'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    dashboard_data: {
      total_news_items: 0,
      total_products: 0,
      report_items_completed: 0,
      report_items_in_progress: 0,
      total_database_items: 0,
      latest_collected: '',
      tag_cloud: {}
    },
    clusters: {}
  }),
  actions: {
    async loadDashboardData() {
      try {
        const response = await getDashboardData()
        this.dashboard_data = response.data
      } catch (error) {
        notifyFailure(error.message)
      }
    },
    async loadClusters(days = null) {
      try {
        const response = await getTrendingClusters(days)
        this.clusters = response.data
      } catch (error) {
        notifyFailure(error.message)
      }
    },
    async getCluster(tag_type, filter_data) {
      try {
        const response = await getCluster(tag_type, filter_data)
        return response.data
      } catch (error) {
        notifyFailure(error.message)
      }
    }
  }
})
