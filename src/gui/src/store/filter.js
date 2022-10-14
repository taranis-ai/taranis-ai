const state = {
  scope: '',

  newsItemsFilter: {
    offset: 0,
    limit: 15,
    group: undefined,
    filter: {
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
  setFilter(context, filter) {
    context.commit('SET_FILTER', filter)
  },
  setOrder(context, order) {
    context.commit('SET_ORDER', order)
  }
}

const getters = {
  getState(state) {
    return state
  },
  getNewsItemsFilter(state) {
    return state.newsItemsFilter
  }
}

const mutations = {
  RESET_NEWSITEMS_FILTERS(state) {
    state.newsItemsFilter = {
      offset: 0,
      limit: 15,
      group: undefined,
      filter: {
        search: undefined,
        sort: undefined,
        range: undefined,
        date: undefined,
        tags: undefined,
        in_analyze: undefined,
        relevant: undefined,
        important: undefined
      }
    }
  },
  SET_SCOPE(state, scope) {
    state.scope = scope
    state.newsItemsFilter.group = scope
  },
  SET_FILTER(state, filter) {
    state.newsItemsFilter.filter = filter
  },
  SET_OREDER(state, order) {
    state.newsItemsFilter.sort = order
  }
}

export const filter = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
