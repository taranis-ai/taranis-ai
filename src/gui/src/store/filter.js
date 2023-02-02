const state = {
  newsItemsFilter: {
    offset: undefined,
    limit: undefined,
    search: undefined,
    sort: 'DATE_DESC',
    range: undefined,
    read: undefined,
    tags: undefined,
    group: undefined,
    source: undefined,
    in_report: undefined,
    relevant: undefined,
    important: undefined
  }
}

const actions = {
  resetNewsItemsFilter(context) {
    context.commit('RESET_NEWSITEMS_FILTERS')
  },
  setLimit(context, limit) {
    context.commit('SET_LIMIT', limit)
  },
  setOffset(context, offset) {
    context.commit('SET_OFFSET', offset)
  },
  setTags(context, tags) {
    context.commit('SET_TAGS', tags)
  },
  incrementOffset(context) {
    context.commit('INCREMENT_OFFSET')
  },
  nextPage(context) {
    context.commit('NEXT_PAGE')
  },
  setFilter(context, filter) {
    context.commit('SET_FILTER', filter)
  },
  updateFilter(context, filter) {
    context.commit('UPDATE_FILTER', filter)
  },
  setSort(context, sort) {
    context.commit('SET_SORT', sort)
  }
}

const getters = {
  getState(state) {
    return state
  },
  getNewsItemsFilter(state) {
    return state.newsItemsFilter
  },
  getOffset(state) {
    return state.newsItemsFilter.offset
  }
}

const mutations = {
  INCREMENT_OFFSET(state) {
    state.newsItemsFilter.offset++
  },
  NEXT_PAGE(state) {
    const offset = state.newsItemsFilter.offset
      ? parseInt(state.newsItemsFilter.offset)
      : 0
    const limit = state.newsItemsFilter.limit
      ? parseInt(state.newsItemsFilter.limit)
      : 20

    state.newsItemsFilter.offset = offset + limit
  },
  RESET_NEWSITEMS_FILTERS(state) {
    state.newsItemsFilter = {
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: 'DATE_DESC',
      range: undefined,
      read: undefined,
      tags: undefined,
      group: undefined,
      source: undefined,
      in_report: undefined,
      relevant: undefined,
      important: undefined
    }
  },
  SET_FILTER(state, filter) {
    state.newsItemsFilter = filter
  },
  UPDATE_FILTER(state, filter) {
    Object.keys(filter).forEach((element) => {
      state.newsItemsFilter[element] = filter[element]
    })
  },
  SET_SORT(state, sort) {
    state.newsItemsFilter.sort = sort
  },
  SET_LIMIT(state, limit) {
    state.newsItemsFilter.limit = limit
  },
  SET_OFFSET(state, offset) {
    state.newsItemsFilter.offset = offset
  },
  SET_TAGS(state, tags) {
    state.newsItemsFilter.tags = tags
  }
}

export const filter = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
