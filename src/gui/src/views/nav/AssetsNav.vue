<template>
  <filter-navigation
    :search="filter.search"
    @update:search="(value) => (search = value)"
    :limit="limit"
    @update:limit="(value) => (limit = value)"
    :offsest="offset"
    @update:offset="(value) => (offset = value)"
  >
    <template #navdrawer>
      <v-row class="my-2 mr-0 px-2 pb-5">
        <v-col cols="12" align-self="center" class="py-1">
          <v-btn @click="addAsset()" color="primary" block>
            <v-icon left dark> mdi-view-grid-plus </v-icon>
            New Asset
          </v-btn>
        </v-col>
        <v-col cols="12" align-self="center" class="py-2">
          <v-btn @click="addAssetGroup()" color="primary" block>
            <v-icon left dark> mdi-folder-plus-outline </v-icon>
            New Asset Group
          </v-btn>
          {{ filter.search }}
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4>sort by</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="sort" :items="orderOptions" />
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex'
import FilterNavigation from '@/components/common/FilterNavigation'
import filterSortList from '@/components/assess/filter/filterSortList'

export default {
  name: 'AssetsNav',
  components: {
    filterSortList,
    FilterNavigation
  },
  data: () => ({
    awaitingSearch: false,
    orderOptions: [
      {
        label: 'date',
        icon: 'mdi-calendar-range-outline',
        type: 'DATE',
        direction: 'DESC'
      },
      {
        label: 'vulnerability',
        icon: 'mdi-counter',
        type: 'VULNERABILITY',
        direction: 'ASC'
      }
    ]
  }),
  computed: {
    ...mapState('filter', {
      filter: (state) => state.assetFilter
    }),
    ...mapState(['drawerVisible']),
    ...mapState('route', ['query']),
    limit: {
      get() {
        return this.filter.limit
      },
      set(value) {
        this.updateAssetFilter({ limit: value })
        this.updateAssets()
      }
    },
    sort: {
      get() {
        if (!this.filter.order) return 'DATE_DESC'
        return this.filter.order
      },
      set(value) {
        this.updateAssetFilter({ sort: value })
        this.updateAssets()
      }
    },
    offset: {
      get() {
        return this.filter.offset
      },
      set(value) {
        this.updateAssetFilter({ offset: value })
        this.updateAssets()
      }
    },
    search: {
      get() {
        return this.filter.search
      },
      set(value) {
        this.updateAssetFilter({ search: value })
        if (!this.awaitingSearch) {
          setTimeout(() => {
            this.updateAssets()
            this.awaitingSearch = false
          }, 500)
        }

        this.awaitingSearch = true
      }
    },
    offsetRange() {
      const list = []
      for (let i = 0; i <= this.getItemCount().total; i++) {
        list.push(i)
      }
      return list
    },
    pages() {
      const blocks = Math.ceil(
        this.getItemCount().total / this.getItemCount().filtered
      )
      const list = []
      for (let i = 0; i <= blocks; i++) {
        list.push(i)
      }
      return list
    },
    navigation_drawer_class() {
      return this.showOmniSearch ? 'mt-12' : ''
    }
  },
  methods: {
    ...mapGetters(['getItemCount']),
    ...mapActions('assets', ['updateAssets']),
    ...mapActions('filter', ['setAssetFilter', 'updateAssetFilter']),
    ...mapGetters('filter', ['getAssetFilter']),
    addAsset() {
      this.$router.push('/asset/0')
    },
    addAssetGroup() {
      this.$router.push('/asset-group/0')
    }
  },
  created() {
    const query = Object.fromEntries(
      Object.entries(this.query).filter(([_, v]) => v != null)
    )
    this.updateAssetFilter(query)
    console.debug('loaded with query', query)
  }
}
</script>
