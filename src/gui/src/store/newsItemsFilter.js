import { getField, updateField } from 'vuex-map-fields'

export const newsItemsFilter = {
  namespaced: true,
  state: {
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
      },
      scope: {
        topics: [],
        sharingSets: [],
        sources: []
      }

    },
    order: {
      selected: {}
    }
  },
  actions: {
    resetNewsItemsFilter(context) {
      context.commit('RESET_NEWSITEMS_FILTERS')
    }
  },
  getters: {
    getField
  },
  mutations: {
    updateField,

    RESET_NEWSITEMS_FILTERS(state) {
      state.filter = {
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
        },
        scope: {
          topics: [],
          sharingSets: [],
          sources: []
        }
      }
      state.order = {
        selected: {}
      }
    }

  }
}
