import {
  getNewsItemsAggregates,
  getOSINTSourceGroupsList,
  getTopStories,
  getNewsItemAggregate,
  getOSINTSourcesList
} from '@/api/assess'
import { filter } from '@/store/filter'
import { xorConcat } from '@/utils/helpers'

const state = {
  multi_select: false,
  selection: [],
  osint_sources: [],
  osint_source_groups: [],
  default_source_group_id: '',
  newsItems: { total_count: 0, items: [] },
  newsItemsSelection: [],
  top_stories: [],
  max_item: null
}

const actions = {
  updateAggregateByID(context, id) {
    return getNewsItemAggregate(id).then((response) => {
      context.commit('UPDATE_NEWSITEMS', [response.data])
    })
  },

  updateNewsItemsByGroup(context, newsItemsFilter) {
    return getNewsItemsAggregates(newsItemsFilter).then((response) => {
      context.commit('UPDATE_NEWSITEMS', response.data)
    })
  },

  updateNewsItems(context) {
    return getNewsItemsAggregates(filter.state.newsItemsFilter).then(
      (response) => {
        context.commit('UPDATE_NEWSITEMS', response.data)
        context.dispatch('updateMaxItem', response.data.items)
      }
    )
  },

  updateOSINTSources(context) {
    return getOSINTSourcesList().then((response) => {
      context.commit('UPDATE_OSINTSOURCES', response.data)
    })
  },

  updateOSINTSourceGroupsList(context) {
    return getOSINTSourceGroupsList().then((response) => {
      context.commit('setOSINTSourceGroups', response.data)
      context.commit('setDefaultOSINTSourceGroup', response.data)
    })
  },

  updateTopStories(context) {
    return getTopStories().then((response) => {
      context.commit('setTopStories', response.data)
    })
  },

  setNewsItems(context, newsItems) {
    context.commit('UPDATE_NEWSITEMS', newsItems)
  },

  selectNewsItem(context, id) {
    context.commit('SELECT_NEWSITEM', id)
  },

  clearNewsItemSelection(context) {
    context.commit('CLEAR_NEWSITEM_SELECTION')
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

  assignSharingSet(context, { items, sharingSet }) {
    context.commit('ASSIGN_SHARINGSET', { items, sharingSet })
  },

  removeStoryFromNewsItem(context, { newsItemId, storyId }) {
    context.commit('REMOVE_TOPIC_FROM_NEWSITEM', { newsItemId, storyId })
  },
  updateMaxItem(context, newsItems) {
    const countsArray = newsItems.map((item) =>
      Math.max(
        ...Object.values(
          item.news_items.reduce((acc, item) => {
            const day = new Date(
              item.news_item_data.published
            ).toLocaleDateString(undefined, {
              day: '2-digit',
              month: '2-digit'
            })
            acc[day] = (acc[day] || 0) + 1
            return acc
          }, {})
        )
      )
    )
    context.commit('UPDATE_MAXITEM', Math.max(...countsArray))
  }
}

const mutations = {
  UPDATE_MAXITEM(state, max_item) {
    state.max_item = max_item
  },

  UPDATE_NEWSITEMS(state, newsItems) {
    state.newsItems = newsItems
  },

  UPDATE_OSINTSOURCES(state, osint_sources) {
    state.osint_sources = osint_sources
  },

  SELECT_NEWSITEM(state, id) {
    state.newsItemsSelection = xorConcat(state.newsItemsSelection, id)
  },

  DESELECT_NEWSITEM(state, id) {
    const index = state.newsItems.findIndex((x) => x.id === id)
    state.newsItems[index].selected = false
    state.newsItemsSelection = state.newsItemsSelection.filter((x) => x !== id)
  },

  DESELECT_ALL_NEWSITEMS(state) {
    state.newsItems.items.forEach((newsItem) => {
      newsItem.selected = false
    })
    state.newsItemsSelection = []
  },

  CLEAR_NEWSITEM_SELECTION(state) {
    state.newsItemsSelection = []
  },

  ASSIGN_SHARINGSET(state, data) {
    data.items.forEach((item) => {
      const index = state.newsItems.findIndex((x) => x.id === item)
      state.newsItems[index].shared = true
      state.newsItems[index].stories.push(data.sharingSet)
      state.newsItems[index].sharingSets.push(data.sharingSet)
    })
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
      if (
        state.selection[i].type === selectedItem.type &&
        state.selection[i].id === selectedItem.id
      ) {
        state.selection.splice(i, 1)
        break
      }
    }
  },

  setOSINTSourceGroups(state, osint_source_groups) {
    state.osint_source_groups = osint_source_groups
  },

  setTopStories(state, top_stories) {
    state.top_stories = top_stories
  },

  setDefaultOSINTSourceGroup(state, osint_source_groups) {
    state.default_source_group_id = osint_source_groups.items.filter(
      (value) => value.default
    )[0].id
  }
}

const getters = {
  getNewsItems(state) {
    return state.newsItems
  },

  getOSINTSourceGroupsList(state) {
    return Array.isArray(state.osint_source_groups.items)
      ? state.osint_source_groups.items.map((value) => ({
          id: value.id,
          title: value.name
        }))
      : []
  },

  getOSINTSourcesList(state) {
    return Array.isArray(state.osint_sources.items)
      ? state.osint_sources.items.map((value) => ({
          id: value.id,
          title: value.name
        }))
      : []
  },

  getScopeFilterList(state) {
    const osint_source_groups = Array.isArray(state.osint_source_groups.items)
      ? state.osint_source_groups.items.map((value) => ({
          id: { type: 'group', id: value.id },
          title: value.name
        }))
      : []
    const osint_sources = Array.isArray(state.osint_sources.items)
      ? state.osint_sources.items.map((value) => ({
          id: { type: 'source', id: value.id },
          title: value.name
        }))
      : []
    return [...osint_source_groups, ...osint_sources]
  },

  getOSINTSourceGroupList(state) {
    return state.osint_source_groups
  },

  getNewsItemById: (state) => (id) => {
    return state.newsItems.find((newsItem) => newsItem.id === id)
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

  getOSINTSources(state) {
    return state.osint_sources
  },
  getMaxItem(state) {
    return state.max_item
  }
}

export const assess = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
