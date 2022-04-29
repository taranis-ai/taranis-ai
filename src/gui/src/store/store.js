import Vue from 'vue'
import Vuex from 'vuex'

import { authenticator } from '@/store/authenticator'
import { assess } from '@/store/assess'
import { config } from '@/store/config'
import { analyze } from '@/store/analyze'
import { publish } from '@/store/publish'
import { settings } from '@/store/settings'
import { assets } from '@/store/assets'
import { dashboard } from '@/store/dashboard'
import { users } from '@/store/users'
import { osint_source } from '@/store/osint_source'
import { newsItemsFilter } from '@/store/newsItemsFilter'
import { topicsFilter } from '@/store/topicsFilter'
import { dummyData } from '@/store/dummyData'

Vue.use(Vuex)

const state = {
  user: {
    id: '',
    name: '',
    organization_name: '',
    permissions: []
  },
  itemCount: {
    total: 0,
    filtered: 0
  }
}

const actions = {

  setUser(context, userData) {
    context.commit('setUser', userData)
  },

  updateItemCount(context, itemCount) {
    context.commit('updateItemCount', itemCount)
  },

  logout(context) {
    context.commit('clearJwtToken')
  }
}

const mutations = {

  setUser(state, userData) {
    state.user = userData
  },

  updateItemCount(state, itemCount) {
    state.itemCount = itemCount
  },
}

const getters = {

  getUserId(state) {
    return state.user.id
  },

  getUserName(state) {
    return state.user.name
  },

  getOrganizationName(state) {
    return state.user.organization_name
  },

  getPermissions(state) {
    return state.user.permissions
  },

  getSelection(state) {
    return state.selection
  },

  getLoadingState(state) {
    return state.loading
  }
}

export const store = new Vuex.Store({
  state,
  actions,
  mutations,
  getters,
  modules: {
    authenticator,
    assess,
    config,
    analyze,
    publish,
    settings,
    assets,
    dashboard,
    users,
    osint_source,
    newsItemsFilter,
    topicsFilter,
    dummyData
  }
})
