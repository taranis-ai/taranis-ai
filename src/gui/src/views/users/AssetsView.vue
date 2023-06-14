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
import { mapActions, mapState, mapWritableState } from 'pinia'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useAssetsStore } from '@/stores/AssetsStore'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'AssetsView',
  components: {},
  data: function () {
    return {
      selected: [],
      assets: [],
      asset_groups: [],
      headers: [
        { title: 'tag', key: 'tag', sortable: false, width: '15px' },
        { title: 'name', key: 'name' },
        { title: 'description', key: 'description' }
      ]
    }
  },
  computed: {
    ...mapWritableState(useMainStore, ['itemCountTotal', 'itemCountFiltered']),
    ...mapState(useAssetsStore, {
      store_asset_groups: 'asset_groups',
      store_assets: 'assets'
    })
  },
  mounted() {
    this.updateData()
  },
  methods: {
    ...mapActions(useAssetsStore, ['loadAssetGroups', 'loadAssets']),
    updateData() {
      this.loadAssets().then(() => {
        const sources = this.store_assets
        this.assets = sources.items
        this.itemCountTotal = sources.total_count
        this.itemCountFiltered = sources.length
      })
      this.loadAssetGroups().then(() => {
        this.asset_groups = this.store_asset_groups.items
      })
    },
    addAsset() {
      this.$router.push('/asset/0')
    },
    editAsset(item) {
      this.$router.push('/asset/' + item.id)
    },
    addAssetGroup() {
      this.$router.push('/asset-group/0')
    },
    editAssetGroup(item) {
      this.$router.push('/asset-group/' + item.id)
    },
    deleteAsset(item) {
      deleteAsset(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    },
    deleteAssetGroup(item) {
      deleteAssetGroup(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    },
    selectionChange(selected) {
      this.selected = selected.map((item) => item.id)
    }
  }
}
</script>
