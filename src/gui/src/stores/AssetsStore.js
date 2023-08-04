import { getAllAssetGroups, getAllAssets } from '@/api/assets'
import { defineStore } from 'pinia'
import { useFilterStore } from './FilterStore'

export const useAssetsStore = defineStore('assets', {
  state: () => ({
    asset_groups: { total_count: 0, items: [] },
    assets: { total_count: 0, items: [] }
  }),
  actions: {
    loadAssetGroups(data) {
      return getAllAssetGroups(data).then((response) => {
        this.asset_groups = response.data
      })
    },
    loadAssets(data) {
      return getAllAssets(data).then((response) => {
        this.assets = response.data
      })
    },
    updateFilteredAssets() {
      const filter = useFilterStore()
      return getAllAssets(filter.assetFilter).then((response) => {
        this.assets = response.data
      })
    }
  }
})
