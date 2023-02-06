import { getDashboardData } from '@/api/dashboard'

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
  stories: []
}

const actions = {

  loadDashboardData(context) {
    return getDashboardData()
      .then(response => {
        context.commit('setDashboardData', response.data)
      })
  },

  loadStories(context) {
    return getDashboardData()
      .then(response => {
        context.commit('setStories', response.data)
      })
  },

  createStory(context, mergedStory) {
    context.commit('createStory', mergedStory)
  }

}

const mutations = {
  setDashboardData (state, data) {
    state.dashboard_data = data
  },

  setStories (state, stories) {
    state.stories = stories
  },

  createStory (state, mergedStory) {
    state.stories.push(mergedStory)
  }

}

const getters = {
  getStories(state) {
    return state.stories
  },

  getDashboardData(state) {
    return state.dashboard_data
  },

  getNewsItemIds: (state) => (id) => {
    return state.stories.find(story => story.id === id).items.ids
  },

  getStoryById: (state) => (id) => {
    return state.stories.find(story => story.id === id)
  },

  getStoryTitleById: (state) => (id) => {
    return state.stories.find(story => story.id === id).title
  }
}

export const dashboard = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
