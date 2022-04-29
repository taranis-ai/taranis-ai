import { getManualOSINTSources, getNewsItemsByGroup } from '@/api/assess'
import { getField, updateField } from 'vuex-map-fields'
import { xor } from 'lodash'

const state = {
  // newsitems: { total_count: 0, items: [] },
  multi_select: false,
  selection: [],
  current_group_id: '',
  manual_osint_sources: [],
  filter: {},
  newsItems: [],
  newsItemsSelection: []
}

const actions = {

  getNewsItemsByGroup(context, data) {
    return getNewsItemsByGroup(data.group_id, data.data)
      .then(response => {
        context.commit('setNewsItems', response.data)
      })
  },

  updateNewsItems(context, newsItems) {
    context.commit('UPDATE_NEWSITEMS', newsItems)
  },

  upvoteNewsItem(context, id) {
    context.commit('UPVOTE_NEWSITEM', id)
  },

  downvoteNewsItem(context, id) {
    context.commit('DOWNVOTE_NEWSITEM', id)
  },

  selectNewsItem(context, id) {
    context.commit('SELECT_NEWSITEM', id)
  },

  deleteNewsItem(context, id) {
    context.commit('DELETE_NEWSITEM', id)
  },

  deselectNewsItem(context, id) {
    context.commit('DESELECT_NEWSITEM', id)
  },

  deselectAllNewsItems(context) {
    context.commit('DESELECT_ALL_NEWSITEMS')
  },

  multiSelect(context, data) {
    context.commit('setMultiSelect', data)
  },

  select(context, data) {
    context.commit('addSelection', data)
  },

  deselect(context, data) {
    context.commit('removeSelection', data)
  },

  changeCurrentGroup(context, data) {
    context.commit('setCurrentGroup', data)
  },

  changeMergeAttr(context, { src, dest }) {
    context.commit('CHANGE_MERGE_ATTR', { src, dest })
  },

  assignSharingSet(context, { items, sharingSet }) {
    context.commit('ASSIGN_SHARINGSET', { items, sharingSet })
  },

  removeTopicFromNewsItem(context, { newsItemId, topicId }) {
    context.commit('REMOVE_TOPIC_FROM_NEWSITEM', { newsItemId, topicId })
  },

  getManualOSINTSources(context) {
    return getManualOSINTSources()
      .then(response => {
        context.commit('setManualOSINTSources', response.data)
      })
  },

  filter(context, data) {
    context.commit('setFilter', data)
  }
}

const mutations = {

  updateField,

  UPDATE_NEWSITEMS(state, newsItems) {
    state.newsItems = newsItems
  },

  SELECT_NEWSITEM(state, id) {
    state.newsItemsSelection = xor(state.newsItemsSelection, [id])
  },

  UPVOTE_NEWSITEM(state, id) {
    const index = state.newsItems.findIndex((x) => x.id === id)
    state.newsItems[index].votes.up += 1
  },

  DOWNVOTE_NEWSITEM(state, id) {
    const index = state.newsItems.findIndex((x) => x.id === id)
    state.newsItems[index].votes.down += 1
  },

  DELETE_NEWSITEM(state, id) {
    state.newsItems = state.newsItems.filter((x) => x.id !== id)
    state.newsItemsSelection = state.newsItemsSelection.filter((x) => x !== id)
  },

  DESELECT_NEWSITEM(state, id) {
    const index = state.newsItems.findIndex((x) => x.id === id)
    state.newsItems[index].selected = false
    state.newsItemsSelection = state.newsItemsSelection.filter((x) => x !== id)
  },

  DESELECT_ALL_NEWSITEMS(state) {
    state.newsItems.forEach((newsItem) => { newsItem.selected = false })
    state.newsItemsSelection = []
  },

  REMOVE_TOPIC_FROM_NEWSITEM(state, data) {
    const newsItem = state.newsItems.find(({ id }) => id === data.newsItemId)
    newsItem.topics = newsItem.topics.filter(
      (topic) => topic !== data.topicId
    )
  },

  ASSIGN_SHARINGSET(state, data) {
    data.items.forEach((item) => {
      const index = state.newsItems.findIndex((x) => x.id === item)
      state.newsItems[index].shared = true
      state.newsItems[index].topics.push(data.sharingSet)
      state.newsItems[index].sharingSets.push(data.sharingSet)
    })
  },

  CHANGE_MERGE_ATTR(state, replacement) {
    replacement.src.forEach(topicToReplace => {
      state.newsItems = [...state.newsItems].map(({ topics, sharingSets, shared, ...rest }) => ({
        topics: topics.map(element => {
          if (topicToReplace === element) {
            return replacement.dest
          }
          return element
        }),
        sharingSets: sharingSets.filter(element => topicToReplace !== element),
        shared: Boolean(sharingSets.length),
        ...rest
      }))
    })
  },

  setNewsItems(state, news_items) {
    state.newsitems = news_items
  },

  setMultiSelect(state, enable) {
    state.multi_select = enable
    state.selection = []
  },

  addSelection(state, selected_item) {
    state.selection.push(selected_item)
  },

  removeSelection(state, selectedItem) {
    for (let i = 0; i < state.selection.length; i++) {
      if (state.selection[i].type === selectedItem.type && state.selection[i].id === selectedItem.id) {
        state.selection.splice(i, 1)
        break
      }
    }
  },

  setCurrentGroup(state, group_id) {
    state.current_group_id = group_id
  },

  setManualOSINTSources(state, new_manual_osint_sources) {
    state.manual_osint_sources = new_manual_osint_sources
  },

  setFilter(state, data) {
    state.filter = data
  }
}

const getters = {

  getField,

  getNewsItems(state) {
    return state.newsItems
  },

  getNewsItemsByTopicId: (state) => (id) => {
    return state.newsItems.filter(newsItem => newsItem.topics.includes(id))
  },

  getNewsItemsByTopicList: (state) => (topicsList) => {
    return state.newsItems.filter(newsItem => {
      return newsItem.topics.some((itemTopics) => topicsList.map((topic) => topic.id).indexOf(itemTopics) >= 0)
    })
  },

  getNewsItemById: (state) => (id) => {
    return state.newsItems.find(newsItem => newsItem.id === id)
  },

  getNewsItemsSelection(state) {
    return state.newsItemsSelection
  },

  getMultiSelect(state) {
    return state.multi_select
  },

  getSelection(state) {
    return state.selection
  },

  getCurrentGroup(state) {
    return state.current_group_id
  },

  getManualOSINTSources(state) {
    return state.manual_osint_sources
  },

  getFilter(state) {
    return state.filter
  },
}

export const assess = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
