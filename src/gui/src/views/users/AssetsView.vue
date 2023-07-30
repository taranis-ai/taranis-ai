<template>
  <v-container fluid>
    <v-card v-for="asset in assets" :key="asset.id" class="mt-3">
      <v-card-title>
        {{ asset.name }}
      </v-card-title>
    </v-card>
    <v-card
      v-for="asset_group in asset_groups"
      :key="asset_group.id"
      class="mt-3"
    >
      <v-card-title>
        {{ asset_group.name }} - {{ asset_group.id }} -
        {{ asset_group.description }}
      </v-card-title>
    </v-card>
  </v-container>
</template>

<script>
import {
  deleteAssetGroup,
  // solveVulnerability,
  deleteAsset
} from '@/api/assets'
import { defineComponent, ref, onMounted } from 'vue'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useAssetsStore } from '@/stores/AssetsStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default defineComponent({
  name: 'AssetsView',
  components: {},
  setup() {
    const selected = ref([])
    const assetsStore = useAssetsStore()
    const mainStore = useMainStore()
    const { asset_groups, assets } = storeToRefs(assetsStore)

    const updateData = () => {
      assetsStore.loadAssets().then(() => {
        mainStore.itemCountTotal = assets.value.total_count
        mainStore.itemCountFiltered = assets.value.length
      })
      assetsStore.loadAssetGroups()
    }

    const addAsset = () => {
      router.push('/asset/0')
    }

    const editAsset = (item) => {
      router.push('/asset/' + item.id)
    }

    const addAssetGroup = () => {
      router.push('/asset-group/0')
    }

    const editAssetGroup = (item) => {
      router.push('/asset-group/' + item.id)
    }

    const deleteAsset = (item) => {
      deleteAsset(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const deleteAssetGroup = (item) => {
      deleteAssetGroup(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const selectionChange = (selected) => {
      selected.value = selected.map((item) => item.id)
    }

    onMounted(() => {
      updateData()
    })

    return {
      selected,
      assets,
      asset_groups,
      addAsset,
      editAsset,
      addAssetGroup,
      editAssetGroup,
      deleteAsset,
      deleteAssetGroup,
      selectionChange
    }
  }
})
</script>
