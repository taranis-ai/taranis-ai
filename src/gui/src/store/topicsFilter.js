import { getField, updateField } from 'vuex-map-fields'

export const topicsFilter = {
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
      }
    },
    order: {
      selected: {},
      keepPinned: true
    }
  },
  actions: {
    resetTopicsFilter(context) {
      context.commit('RESET_TOPICS_FILTERS')
    }
  },
  getters: {
    getField
  },
  mutations: {
    updateField,

    RESET_TOPICS_FILTERS(state) {
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
        }
      }
      state.order = {
        selected: {},
        keepPinned: true
      }
    }
  }
}
