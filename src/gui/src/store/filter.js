const state = {
  scope: '',

  newsItemsFilter: {
    offset: 0,
    limit: 15,
    search: undefined,
    sort: 'DATE_DESC',
    range: undefined,
    date: undefined,
    tags: undefined,
    in_analyze: undefined,
    relevant: undefined,
    important: undefined
  },
  newsItemsOrder: {
    selected: {}
  }
}

const actions = {
  resetNewsItemsFilter(context) {
    context.commit('RESET_NEWSITEMS_FILTERS')
  },
  setScope(context, scope) {
    context.commit('SET_SCOPE', scope)
  },
  setLimit(context, limit) {
    context.commit('SET_LIMIT', limit)
  },
  setOffset(context, offset) {
    context.commit('SET_OFFSET', offset)
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
    state.newsItemsFilter.offset = state.newsItemsFilter.offset + state.newsItemsFilter.limit
  },
  RESET_NEWSITEMS_FILTERS(state) {
    state.newsItemsFilter = {
      offset: 0,
      limit: 15,
      search: undefined,
      sort: undefined,
      range: undefined,
      date: undefined,
      tags: undefined,
      in_analyze: undefined,
      relevant: undefined,
      important: undefined
    }
  },
  SET_SCOPE(state, scope) {
    state.scope = scope
  },
  SET_FILTER(state, filter) {
    state.newsItemsFilter = filter
  },
  UPDATE_FILTER(state, filter) {
    Object.keys(filter).forEach(element => {
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
  }
}

export const filter = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
