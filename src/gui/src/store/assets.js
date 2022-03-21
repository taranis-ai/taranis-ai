import { getAllAssetGroups, getAllAssets, getAllNotificationTemplates } from '@/api/assets'

const state = {
  asset_groups: { total_count: 0, items: [] },
  notification_templates: { total_count: 0, items: [] },
  assets: { total_count: 0, items: [] }
}

const actions = {

  getAllAssetGroups (context, data) {
    return getAllAssetGroups(data)
      .then(response => {
        context.commit('setAssetGroups', response.data)
      })
  },

  getAllAssets (context, data) {
    return getAllAssets(data)
      .then(response => {
        context.commit('setAssets', response.data)
      })
  },

  getAllNotificationTemplates (context, data) {
    return getAllNotificationTemplates(data)
      .then(response => {
        context.commit('setNotificationTemplates', response.data)
      })
  }
}

const mutations = {

  setAssetGroups (state, new_asset_groups) {
    state.asset_groups = new_asset_groups
  },

  setAssets (state, new_assets) {
    state.assets = new_assets
  },

  setNotificationTemplates (state, new_notification_templates) {
    state.notification_templates = new_notification_templates
  }
}

const getters = {

  getAssetGroups (state) {
    return state.asset_groups
  },

  getAssets (state) {
    return state.assets
  },

  getNotificationTemplates (state) {
    return state.notification_templates
  }
}

export const assets = {
  state,
  actions,
  mutations,
  getters
}
