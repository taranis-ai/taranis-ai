import { defineStore } from 'pinia'
import {
  getDashboardData,
  getTrendingClusters,
  getClusterByType
} from '@/api/dashboard'
import { ref } from 'vue'
import { notifyFailure } from '@/utils/helpers'

export const useDashboardStore = defineStore('dashboard', () => {
  const dashboard_data = ref({
    total_news_items: 0,
    total_products: 0,
    report_items_completed: 0,
    report_items_in_progress: 0,
    total_database_items: 0,
    latest_collected: '',
    tag_cloud: {},
    conflict_count: 0
  })

  const clusters = ref({})

  async function loadDashboardData() {
    try {
      const response = await getDashboardData()
      dashboard_data.value = response.data
    } catch (error) {
      notifyFailure(error.message)
    }
  }
  async function loadClusters(days = null) {
    try {
      const response = await getTrendingClusters(days)
      clusters.value = response.data
    } catch (error) {
      notifyFailure(error.message)
    }
  }
  async function getCluster(tag_type, filter_data) {
    try {
      const response = await getClusterByType(tag_type, filter_data)
      return response.data
    } catch (error) {
      notifyFailure(error.message)
    }
  }
  function reset() {
    dashboard_data.value = {
      total_news_items: 0,
      total_products: 0,
      report_items_completed: 0,
      report_items_in_progress: 0,
      total_database_items: 0,
      latest_collected: '',
      tag_cloud: {},
      conflict_count: 0
    }
    clusters.value = {}
  }

  return {
    dashboard_data,
    clusters,
    loadDashboardData,
    loadClusters,
    getCluster,
    reset
  }
})
