import { getDashboardData, getTrendingClusters } from '@/api/dashboard'

const state = {
  dashboard_data: {
    total_news_items: 0,
    total_products: 0,
    report_items_completed: 0,
    report_items_in_progress: 0,
    total_database_items: 0,
    latest_collected: '',
    tag_cloud: {}
  },
  clusters: []
}

const actions = {

  loadDashboardData(context) {
    return getDashboardData()
      .then(response => {
        context.commit('setDashboardData', response.data)
      })
  },

  loadClusters(context) {
    return getTrendingClusters()
      .then(response => {
        context.commit('setClusters', response.data)
      })
  }
}

const mutations = {
  setDashboardData (state, data) {
    state.dashboard_data = data
  },

  setClusters (state, clusters) {
    state.clusters = clusters
  }
}

const getters = {
  getClusters(state) {
    return state.clusters
  },

  getDashboardData(state) {
    return state.dashboard_data
  }
}

export const dashboard = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
