import { getDashboardData } from '@/api/dashboard'
import { getField, updateField } from 'vuex-map-fields'
import { xorConcat } from '@/utils/helpers'

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
  topics: [],
  topicSelection: []
}

const actions = {

  getAllDashboardData(context) {
    return getDashboardData()
      .then(response => {
        context.commit('setDashboardData', response.data)
      })
  },

  updateTopics(context, topics) {
    context.commit('UPDATE_TOPICS', topics)
  },

  updateTopic(context, topic) {
    context.commit('UPDATE_TOPIC', topic)
  },

  pinTopic(context, id) {
    context.commit('PIN_TOPIC', id)
  },

  upvoteTopic(context, id) {
    context.commit('UPVOTE_TOPIC', id)
  },

  downvoteTopic(context, id) {
    context.commit('DOWNVOTE_TOPIC', id)
  },

  selectTopic(context, id) {
    context.commit('SELECT_TOPIC', id)
  },

  unselectAllTopics(context) {
    context.commit('UNSELECT_ALL_TOPICS')
  },

  removeTopicById(context, id) {
    context.commit('REMOVE_TOPIC', id)
  },

  createNewTopic(context, mergedTopic) {
    context.commit('CREATE_TOPIC', mergedTopic)
  }

}

const mutations = {

  updateField,

  UPDATE_TOPICS(state, topics) {
    state.topics = topics
  },

  UPDATE_TOPIC(state, topic) {
    const index = state.topics.findIndex((x) => x.id === topic.id)
    state.topics[index] = topic
  },

  PIN_TOPIC(state, id) {
    for (const topic of state.topics) {
      if (topic.id === id) {
        topic.pinned = !topic.pinned
        break
      }
    }
  },

  UPVOTE_TOPIC(state, id) {
    for (const topic of state.topics) {
      if (topic.id === id) {
        topic.votes.up += 1
        break
      }
    }
  },

  DOWNVOTE_TOPIC(state, id) {
    for (const topic of state.topics) {
      if (topic.id === id) {
        topic.votes.down += 1
        break
      }
    }
  },

  SELECT_TOPIC(state, id) {
    state.topicSelection = xorConcat(state.topicSelection, [id])
  },

  UNSELECT_ALL_TOPICS(state) {
    state.topicSelection = []
    state.topics.forEach(element => {
      element.selected = false
    })
  },

  REMOVE_TOPIC(state, id) {
    state.topics = [...state.topics].filter((topic) => topic.id !== id)
  },

  CREATE_TOPIC(state, newTopic) {
    // Assign new ID
    state.topics.push(newTopic)
  }

}

const getters = {

  getField,

  getTopics(state) {
    return state.topics
  },

  getTopicSelection(state) {
    return state.topicSelection
  },

  getTopicSelectionList(state) {
    const filteredTopics = state.topics.filter((topic) => !topic.isSharingSet)
    return filteredTopics.map(function (topic) { return { id: topic.id, title: topic.title } })
  },

  getSharingSetSelectionList(state) {
    const filteredTopics = state.topics.filter((topic) => topic.isSharingSet)
    return filteredTopics.map(function (topic) { return { id: topic.id, title: topic.title } })
  },

  getDashboardData(state) {
    return state.dashboard_data
  },

  getNewsItemIds: (state) => (id) => {
    return state.topics.find(topic => topic.id === id).items.ids
  },

  getTopicById: (state) => (id) => {
    return state.topics.find(topic => topic.id === id)
  },

  getTopicTitleById: (state) => (id) => {
    return state.topics.find(topic => topic.id === id).title
  }
}

export const dashboard = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
