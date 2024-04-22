<template>
  <v-container fluid>
    <v-expansion-panels multiple>
      <v-expansion-panel v-for="(group, i) in asset_groups.items" :key="i">
        <v-expansion-panel-title>
          {{ group.name }}
          <template #actions>
            <v-icon icon="mdi-menu-down" />
          </template>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list dense>
            <v-list-item
              v-for="asset in assets_by_group[group.id]"
              :key="asset.id"
            >
              <v-list-item-title>{{ asset.name }}</v-list-item-title>
              <v-list-item-subtitle>
                Serial: {{ asset.serial }} Description: {{ asset.description }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
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
  setup() {
    const selected = ref([])
    const assetsStore = useAssetsStore()
    const mainStore = useMainStore()
    const { asset_groups, assets_by_group, assets } = storeToRefs(assetsStore)

    const updateData = () => {
      assetsStore.loadAssets().then(() => {
        mainStore.itemCountTotal = assets.value.total_count
        mainStore.itemCountFiltered = assets.value.length
      })
      assetsStore.loadAssetGroups()
    }

    const addAsset = () => {
      router.push('/asset/')
    }

    const editAsset = (item) => {
      router.push('/asset/' + item.id)
    }

    const addAssetGroup = () => {
      router.push('/asset-group/')
    }

    const editAssetGroup = (item) => {
      router.push('/asset-group/' + item.id)
    }

    const deleteItem = (item) => {
      deleteAsset(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const deleteItemGroup = (item) => {
      deleteAssetGroup(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    onMounted(() => {
      updateData()
    })

    return {
      selected,
      assets_by_group,
      asset_groups,
      addAsset,
      editAsset,
      addAssetGroup,
      editAssetGroup,
      deleteItem,
      deleteItemGroup,
      selectionChange
    }
  }
})
</script>
