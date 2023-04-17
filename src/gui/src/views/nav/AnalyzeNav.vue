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
          <v-btn @click="addReport()" color="primary" block>
            <v-icon left dark> mdi-file-document-plus-outline </v-icon>
            New Report
          </v-btn>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>
      <v-row class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4>filter</h4>
        </v-col>

        <!-- time tags -->
        <v-col cols="12" class="pb-0">
          <date-chips v-model="range" />
        </v-col>

        <v-col cols="12" class="pt-1">
          <filter-select-list
            v-model="filterAttribute"
            :items="filterAttributeOptions"
          />
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
import dateChips from '@/components/assess/filter/dateChips'
import filterSelectList from '@/components/assess/filter/filterSelectList'

export default {
  name: 'AnalyzeNav',
  components: {
    dateChips,
    filterSelectList,
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
      }
    ],
    filterAttributeOptions: [
      { type: 'completed', label: 'completed', icon: 'mdi-progress-check' },
      { type: 'incomplete', label: 'incomplete', icon: 'mdi-progress-close' }
    ],
    filterAttributeSelections: []
  }),
  computed: {
    ...mapState('filter', {
      filter: (state) => state.reportFilter
    }),
    ...mapState(['drawerVisible']),
    ...mapState('route', ['query']),
    limit: {
      get() {
        return this.filter.limit
      },
      set(value) {
        this.updateReportFilter({ limit: value })
        this.updateReportItems()
      }
    },
    sort: {
      get() {
        if (!this.filter.order) return 'DATE_DESC'
        return this.filter.order
      },
      set(value) {
        this.updateReportFilter({ sort: value })
        this.updateReportItems()
      }
    },
    offset: {
      get() {
        return this.filter.offset
      },
      set(value) {
        this.updateReportFilter({ offset: value })
        this.updateReportItems()
      }
    },
    range: {
      get() {
        return this.filter.range
      },
      set(value) {
        this.updateReportFilter({ range: value })
        this.updateReportItems()
      }
    },
    search: {
      get() {
        return this.filter.search
      },
      set(value) {
        this.updateReportFilter({ search: value })
        if (!this.awaitingSearch) {
          setTimeout(() => {
            this.updateReportItems()
            this.awaitingSearch = false
          }, 500)
        }

        this.awaitingSearch = true
      }
    },
    filterAttribute: {
      get() {
        return this.filterAttributeSelections
      },
      set(value) {
        this.filterAttributeSelections = value

        const filterUpdate = this.filterAttributeOptions.reduce((obj, item) => {
          obj[item.type] = value.includes(item.type) ? 'true' : undefined
          return obj
        }, {})

        console.debug('filterAttributeSelections', filterUpdate)
        this.updateReportFilter(filterUpdate)
        this.updateReportItems()
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
    ...mapActions('analyze', ['updateReportItems']),
    ...mapActions('filter', ['setReportFilter', 'updateReportFilter']),
    ...mapGetters('filter', ['getReportFilter']),
    addReport() {
      this.$router.push('/report/0')
    }
  },
  created() {
    const query = Object.fromEntries(
      Object.entries(this.query).filter(([, v]) => v != null)
    )
    this.updateReportFilter(query)
    console.debug('loaded with query', query)
  }
}
</script>
