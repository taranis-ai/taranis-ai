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
  stories: [],
  storySelection: []
}

const actions = {

  getAllDashboardData(context) {
    return getDashboardData()
      .then(response => {
        context.commit('setDashboardData', response.data)
      })
  },

  updateStories(context, stories) {
    context.commit('UPDATE_TOPICS', stories)
  },

  updateStory(context, story) {
    context.commit('UPDATE_TOPIC', story)
  },

  pinStory(context, id) {
    context.commit('PIN_TOPIC', id)
  },

  upvoteStory(context, id) {
    context.commit('UPVOTE_TOPIC', id)
  },

  downvoteStory(context, id) {
    context.commit('DOWNVOTE_TOPIC', id)
  },

  selectStory(context, id) {
    context.commit('SELECT_TOPIC', id)
  },

  unselectAllStories(context) {
    context.commit('UNSELECT_ALL_TOPICS')
  },

  removeStoryById(context, id) {
    context.commit('REMOVE_TOPIC', id)
  },

  createStory(context, mergedStory) {
    context.commit('CREATE_TOPIC', mergedStory)
  }

}

const mutations = {

  updateField,

  UPDATE_TOPICS(state, stories) {
    state.stories = stories
  },

  UPDATE_TOPIC(state, story) {
    const index = state.stories.findIndex((x) => x.id === story.id)
    state.stories[index] = story
  },

  PIN_TOPIC(state, id) {
    for (const story of state.stories) {
      if (story.id === id) {
        story.pinned = !story.pinned
        break
      }
    }
  },

  UPVOTE_TOPIC(state, id) {
    for (const story of state.stories) {
      if (story.id === id) {
        story.votes.up += 1
        break
      }
    }
  },

  DOWNVOTE_TOPIC(state, id) {
    for (const story of state.stories) {
      if (story.id === id) {
        story.votes.down += 1
        break
      }
    }
  },

  SELECT_TOPIC(state, id) {
    state.storySelection = xorConcat(state.storySelection, [id])
  },

  UNSELECT_ALL_TOPICS(state) {
    state.storySelection = []
    state.stories.forEach(element => {
      element.selected = false
    })
  },

  REMOVE_TOPIC(state, id) {
    state.stories = [...state.stories].filter((story) => story.id !== id)
  },

  CREATE_TOPIC(state, newStory) {
    // Assign new ID
    state.stories.push(newStory)
  }

}

const getters = {

  getField,

  getStories(state) {
    return state.stories
  },

  getStorieSelection(state) {
    return state.storySelection
  },

  getStorieSelectionList(state) {
    const filteredStories = state.stories.filter((story) => !story.isSharingSet)
    return filteredStories.map(function (story) { return { id: story.id, title: story.title } })
  },

  getSharingSetSelectionList(state) {
    const filteredStories = state.stories.filter((story) => story.isSharingSet)
    return filteredStories.map(function (story) { return { id: story.id, title: story.title } })
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
