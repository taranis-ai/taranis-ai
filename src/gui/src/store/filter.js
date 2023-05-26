const state = {
  newsItemsFilter: {
    offset: undefined,
    limit: undefined,
    search: undefined,
    sort: undefined,
    range: undefined,
    read: undefined,
    tags: undefined,
    group: undefined,
    source: undefined,
    in_report: undefined,
    relevant: undefined,
    important: undefined
  },
  assetFilter: {
    offset: undefined,
    limit: undefined,
    search: undefined,
    sort: undefined
  },
  reportFilter: {
    offset: undefined,
    limit: undefined,
    search: undefined,
    sort: undefined,
    range: undefined,
    completed: undefined
  },
  productFilter: {
    offset: undefined,
    limit: undefined,
    search: undefined,
    sort: undefined,
    range: undefined
  },
  chartFilter: {
    threshold: 20,
    y2max: undefined
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
  appendTag(context, tag) {
    context.commit('APPEND_TAG', tag)
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
  },
  updateAssetFilter(context, filter) {
    context.commit('UPDATE_ASSET_FILTER', filter)
  },
  setAssetFilter(context, filter) {
    context.commit('SET_ASSET_FILTER', filter)
  },
  updateReportFilter(context, filter) {
    context.commit('UPDATE_REPORT_FILTER', filter)
  },
  setReportFilter(context, filter) {
    context.commit('SET_REPORT_FILTER', filter)
  },
  updateProductFilter(context, filter) {
    context.commit('UPDATE_PRODUCT_FILTER', filter)
  },
  setProductFilter(context, filter) {
    context.commit('SET_PRODUCT_FILTER', filter)
  },
  setThreshold(context, threshold) {
    context.commit('SET_THRESHHOLD', threshold)
  },
  setY2Max(context, y2max) {
    context.commit('SET_y2max', y2max)
  }
}

const getters = {
  getState(state) {
    return state
  },
  getNewsItemsFilter(state) {
    return state.newsItemsFilter
  },
  getAssetFilter(state) {
    return state.assetFilter
  },
  getReportFilter(state) {
    return state.reportFilter
  },
  getProductFilter(state) {
    return state.productFilter
  },
  getOffset(state) {
    return state.newsItemsFilter.offset
  },
  getFilterTags(state) {
    if (typeof state.newsItemsFilter.tags === 'string') {
      return [state.newsItemsFilter.tags]
    }
    return state.newsItemsFilter.tags
  },
  getThreshold(state) {
    return state.chartFilter.threshold
  },
  getY2max(state) {
    return state.chartFilter.y2max
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
      sort: undefined,
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
  SET_ASSET_FILTER(state, filter) {
    state.assetFilter = filter
  },
  UPDATE_ASSET_FILTER(state, filter) {
    Object.keys(filter).forEach((element) => {
      state.assetFilter[element] = filter[element]
    })
  },
  SET_REPORT_FILTER(state, filter) {
    state.reportFilter = filter
  },
  UPDATE_REPORT_FILTER(state, filter) {
    Object.keys(filter).forEach((element) => {
      state.reportFilter[element] = filter[element]
    })
  },
  SET_PRODUCT_FILTER(state, filter) {
    state.productFilter = filter
  },
  UPDATE_PRODUCT_FILTER(state, filter) {
    Object.keys(filter).forEach((element) => {
      state.productFilter[element] = filter[element]
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
  },
  APPEND_TAG(state, tag) {
    if (state.newsItemsFilter.tags) {
      state.newsItemsFilter.tags.push(tag)
    } else {
      state.newsItemsFilter.tags = [tag]
    }
  },
  SET_THRESHHOLD(state, threshold) {
    state.chartFilter.threshold = threshold
  },
  SET_y2max(state, y2max) {
    state.chartFilter.y2max = y2max
  }
}

export const filter = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
