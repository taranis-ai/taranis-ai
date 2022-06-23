import { getField, updateField } from 'vuex-map-fields'

export const filter = {
  namespaced: true,
  state: {
    topicsFilter: {
      filter: {
        search: '',
        attributes: {
          selected: []
        },
        tags: {
          andOperator: true,
          selected: []
        },
        date: {
          range: [],
          selected: 'all'
        }
      },
      order: {
        selected: {},
        keepPinned: true
      }
    },
    newsItemsFilter: {
      scope: {
        topics: [],
        sharingSets: [],
        sources: []
      },
      filter: {
        search: '',
        attributes: {
          selected: []
        },
        tags: {
          andOperator: true,
          selected: []
        },
        date: {
          range: [],
          selected: 'all'
        }
      },
      order: {
        selected: {}
      }
    }
  },

  actions: {
    resetTopicsFilter(context) {
      context.commit('RESET_TOPICS_FILTERS')
    },

    resetNewsItemsFilter(context) {
      context.commit('RESET_NEWSITEMS_FILTERS')
    }
  },

  getters: {
    getField,

    getState(filter) {
      return filter.state
    }
  },

  mutations: {
    updateField,

    RESET_TOPICS_FILTERS(state) {
      state.newsItems = {
        scope: {
          topics: [],
          sharingSets: [],
          sources: []
        },
        filter: {
          search: '',
          attributes: {
            selected: []
          },
          tags: {
            andOperator: true,
            selected: []
          },
          date: {
            range: [],
            selected: 'all'
          }
        },
        order: {
          selected: {},
          keepPinned: true
        }
      }
    },

    RESET_NEWSITEMS_FILTERS(state) {
      state.newsItems = {
        scope: {
          topics: [],
          sharingSets: [],
          sources: []
        },
        filter: {
          search: '',
          attributes: {
            selected: []
          },
          tags: {
            andOperator: true,
            selected: []
          },
          date: {
            range: [],
            selected: 'all'
          }
        },
        order: {
          selected: {}
        }
      }
    }
  }
}
