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
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'AssetsView',
  components: {},
  data: function () {
    return {
      selected: [],
      assets: [],
      asset_groups: [],
      headers: [
        { text: 'tag', value: 'tag', sortable: false, width: '15px' },
        { text: 'name', value: 'name' },
        { text: 'description', value: 'description' }
      ]
    }
  },
  methods: {
    ...mapActions('assets', ['loadAssetGroups', 'loadAssets']),
    ...mapGetters('assets', ['getAssetGroups', 'getAssets']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadAssets().then(() => {
        const sources = this.getAssets()
        this.assets = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
      this.loadAssetGroups().then(() => {
        this.asset_groups = this.getAssetGroups().items
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
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
