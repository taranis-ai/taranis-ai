<template>
  <filter-navigation
    :search="assetFilter.search"
    :limit="limit"
    :offsest="offset"
    @update:search="(value) => (search = value)"
    @update:limit="(value) => (limit = value)"
    @update:offset="(value) => (offset = value)"
  >
    <template #navdrawer>
      <v-row class="my-2 mr-0 px-2 pb-5">
        <v-col cols="12" align-self="center" class="py-1">
          <v-btn color="primary" block @click="addAsset()">
            <v-icon left dark> mdi-view-grid-plus </v-icon>
            New Asset
          </v-btn>
        </v-col>
        <v-col cols="12" align-self="center" class="py-2">
          <v-btn color="primary" block @click="addAssetGroup()">
            <v-icon left dark> mdi-folder-plus-outline </v-icon>
            New Asset Group
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import { mapActions, mapState } from 'pinia'

import FilterNavigation from '@/components/common/FilterNavigation.vue'
import { useAssetsStore } from '@/stores/AssetsStore'
import { useFilterStore } from '@/stores/FilterStore'

export default {
  name: 'AssetsNav',
  components: {
    FilterNavigation
  },
  data: () => ({
    awaitingSearch: false
  }),
  computed: {
    ...mapState(useFilterStore, ['assetFilter']),
    limit: {
      get() {
        return this.assetFilter.limit
      },
      set(value) {
        this.updateAssetFilter({ limit: value })
        this.updateFilteredAssets()
      }
    },
    sort: {
      get() {
        if (!this.assetFilter.order) return 'DATE_DESC'
        return this.assetFilter.order
      },
      set(value) {
        this.updateAssetFilter({ sort: value })
        this.updateFilteredAssets()
      }
    },
    offset: {
      get() {
        return this.assetFilter.offset
      },
      set(value) {
        this.updateAssetFilter({ offset: value })
        this.updateFilteredAssets()
      }
    },
    search: {
      get() {
        return this.assetFilter.search
      },
      set(value) {
        this.updateAssetFilter({ search: value })
        if (!this.awaitingSearch) {
          setTimeout(() => {
            this.updateFilteredAssets()
            this.awaitingSearch = false
          }, 500)
        }

        this.awaitingSearch = true
      }
    },
    navigation_drawer_class() {
      return this.showOmniSearch ? 'mt-12' : ''
    }
  },
  created() {
    const query = Object.fromEntries(
      Object.entries(this.$route.query).filter(([, v]) => v != null)
    )
    this.updateAssetFilter(query)
    console.debug('loaded with query', query)
  },
  methods: {
    ...mapActions(useAssetsStore, ['updateFilteredAssets']),
    ...mapActions(useFilterStore, ['updateAssetFilter']),
    addAsset() {
      this.$router.push('/asset/0')
    },
    addAssetGroup() {
      this.$router.push('/asset-group/0')
    }
  }
}
</script>
