import { getAllAssetGroups, getAllAssets } from '@/api/assets'
import { defineStore } from 'pinia'
import { useFilterStore } from './FilterStore'
import { notifyFailure } from '@/utils/helpers'
import { ref, computed } from 'vue'

export const useAssetsStore = defineStore(
  'assets',
  () => {
    const asset_groups = ref({ total_count: 0, items: [] })
    const assets = ref({ total_count: 0, items: [] })

    const assets_by_group = computed(() => {
      return assets.value.items.reduce((acc, asset) => {
        if (!acc[asset.asset_group_id]) {
          acc[asset.asset_group_id] = []
        }
        acc[asset.asset_group_id].push(asset)
        return acc
      }, {})
    })

    async function loadAssetGroups(data) {
      try {
        const response = await getAllAssetGroups(data)
        console.log(response.data)
        asset_groups.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }
    async function loadAssets(data) {
      try {
        const response = await getAllAssets(data)
        console.log(response.data)
        assets.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }
    async function updateFilteredAssets() {
      try {
        const filter = useFilterStore()
        const response = await getAllAssets(filter.assetFilter)
        assets.value = response.data
      } catch (error) {
        notifyFailure(error)
      }
    }

    function reset() {
      asset_groups.value = []
      assets.value = []
    }

    return {
      assets_by_group,
      asset_groups,
      assets,
      loadAssetGroups,
      loadAssets,
      updateFilteredAssets,
      reset
    }
  },
  {
    persist: true
  }
)
