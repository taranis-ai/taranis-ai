<template>
  <v-container fluid>
    <v-expansion-panels multiple>
      <v-expansion-panel v-for="(group, i) in asset_groups" :key="i">
        <v-expansion-panel-title
          >{{ group.name }}
          <v-btn
            v-if="filterAssets(group.id).length === 0"
            class="ml-5"
            prepend-icon="mdi-delete"
            size="x-small"
            @click.stop="deleteItemGroup(group.id)"
          >
            Delete Empty Group
          </v-btn>

          <template #actions>
            <v-icon icon="mdi-menu-down" />
          </template>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-list dense>
            <v-list-item v-for="(asset, j) in filterAssets(group.id)" :key="j">
              <v-list-item-title>{{ asset.name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ asset.description }}
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
    const { asset_groups, assets } = storeToRefs(assetsStore)

    const updateData = () => {
      assetsStore.loadAssets().then(() => {
        mainStore.itemCountTotal = assets.value.total_count
        mainStore.itemCountFiltered = assets.value.length
      })
      assetsStore.loadAssetGroups()
    }

    const filterAssets = (groupId) => {
      return assets.value.filter((asset) => asset.asset_group_id === groupId)
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
      assets,
      asset_groups,
      addAsset,
      editAsset,
      addAssetGroup,
      editAssetGroup,
      deleteItem,
      filterAssets,
      deleteItemGroup,
      selectionChange
    }
  }
})
</script>
