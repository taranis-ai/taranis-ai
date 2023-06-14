import { defineStore } from 'pinia'

export const useMainStore = defineStore('main', {
  state: () => ({
    user: {
      id: '',
      name: '',
      organization_name: '',
      permissions: []
    },
    vertical_view: false,
    itemCountTotal: 0,
    itemCountFiltered: 0,
    drawerVisible: true,
    coreAPIURL: '/api',
    notification: { message: '', type: '', show: false }
  }),
  getters: {
    getItemCount(state) {
      return { total: state.itemCountTotal, filtered: state.itemCountFiltered }
    }
  },
  actions: {
    toggleDrawer() {
      this.drawerVisible = !this.drawerVisible
    },
    resetItemCount() {
      this.itemCountTotal = 0
      this.itemCountFiltered = 0
    }
  },
  persist: true
})
