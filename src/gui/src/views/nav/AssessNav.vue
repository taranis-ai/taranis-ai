<template>
  <v-navigation-drawer
    clipped
    app
    color="cx-drawer-bg"
    class="sidebar"
    style="max-height: 100% !important; height: calc(100vh - 48px) !important"
    v-if="drawerVisible"
  >
    <v-container class="pa-0">
      <!-- scope -->
      <v-row class="my-3 mr-0 px-3">
        <v-col cols="12" class="pb-0">
          <h4>scope</h4>
        </v-col>

        <v-col cols="12" class="pt-0">
          <v-select
            v-model="scope"
            :items="getScopeFilterList()"
            prepent-icon="mdi-format-list-numbered"
            item-text="title"
            item-value="id"
            label="Sources"
            :hide-details="true"
            solo
            dense
          ></v-select>
        </v-col>
        <v-col cols="6" class="pt-0 pb-0">
          <h4>Display</h4>
          <v-select
            v-model="limit"
            :items="items_per_page"
            label="display items"
            :hide-details="true"
            solo
            dense
          ></v-select>
        </v-col>
        <v-col cols="6" class="pt-0 pb-0">
          <h4>Offset</h4>
          <v-select
            v-model="offset"
            :items="offsetRange"
            :hide-details="true"
            label="offset"
            solo
            dense
          ></v-select>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <!-- search -->
      <v-row class="my-3 mr-0 px-3">
        <v-col cols="12" class="py-0">
          <h4>search</h4>
        </v-col>

        <v-col cols="12">
          <v-text-field
            v-model="search"
            label="search"
            outlined
            dense
            hide-details
            append-icon="mdi-magnify"
          ></v-text-field>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <!-- filter results -->
      <v-row class="my-3 mr-0 px-3">
        <v-col cols="12" class="py-0">
          <h4>filter results</h4>
        </v-col>

        <!-- time tags -->
        <v-col cols="12" class="pb-0">
          <date-chips v-model="range" @input="filter.range = []" />
        </v-col>

        <!-- tags -->
        <v-col cols="12" class="pr-0">
          <tag-filter v-model="tags" />
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-3">
        <v-col cols="12" class="pt-1">
          <filter-selectList
            v-model="filterAttributeSelections"
            :items="filterAttributeOptions"
          />
        </v-col>
      </v-row>

      <v-divider class="mt-2 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-3">
        <v-col cols="12" class="py-0">
          <h4>sort by</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="sort" :items="orderOptions" />
        </v-col>
      </v-row>

      <v-divider class="mt-2 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-3 pb-5">
        <v-col cols="12" class="py-0">
          <v-btn @click="updateNewsItems()" color="primary" block>
            Reload
            <v-icon right dark> mdi-reload </v-icon>
          </v-btn>
        </v-col>
      </v-row>
    </v-container>
  </v-navigation-drawer>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex'
import dateChips from '@/components/_subcomponents/dateChips'
import tagFilter from '@/components/_subcomponents/tagFilter'
import filterSelectList from '@/components/_subcomponents/filterSelectList'
import filterSortList from '@/components/_subcomponents/filterSortList'

export default {
  name: 'AssessNav',
  components: {
    dateChips,
    tagFilter,
    filterSelectList,
    filterSortList
  },
  data: () => ({
    awaitingSearch: false,
    filterAttributeSelections: {},
    filterAttributeOptions: [
      { type: 'unread', label: 'unread', icon: 'mdi-email-mark-as-unread' },
      {
        type: 'important',
        label: 'important',
        icon: 'mdi-exclamation'
      },
      {
        type: 'shared',
        label: 'items in reports',
        icon: 'mdi-share-outline'
      },
      {
        type: 'selected',
        label: 'selected',
        icon: 'mdi-checkbox-marked-outline'
      }
    ],
    orderOptions: [
      {
        label: 'published date',
        icon: 'mdi-calendar-range-outline',
        type: 'DATE',
        direction: 'DESC'
      },
      {
        label: 'relevance',
        icon: 'mdi-counter',
        type: 'RELEVANCE',
        direction: 'DESC'
      }
    ],
    items_per_page: [5, 15, 25, 50, 100]
  }),
  computed: {
    ...mapState('filter', {
      scopeState: (state) => state.scope,
      filter: (state) => state.newsItemsFilter
    }),
    ...mapState(['drawerVisible']),
    ...mapState('route', ['query']),
    scope: {
      get() {
        return this.scopeState
      },
      set(value) {
        this.setScope(value)
        this.updateNewsItems()
      }
    },
    limit: {
      get() {
        return this.filter.limit
      },
      set(value) {
        this.setLimit(value)
        this.updateNewsItems()
      }
    },
    sort: {
      get() {
        return this.filter.order
      },
      set(value) {
        this.setSort(value)
        this.updateNewsItems()
      }
    },
    offset: {
      get() {
        return this.filter.offset
      },
      set(value) {
        this.setOffset(value)
        this.updateNewsItems()
      }
    },
    tags: {
      get() {
        return this.filter.tags
      },
      set(value) {
        this.setTags(value)
        this.updateNewsItems()
      }
    },
    range: {
      get() {
        return this.filter.range
      },
      set(value) {
        this.setRange(value)
        this.updateNewsItems()
      }
    },
    search: {
      get() {
        return this.filter.search
      },
      set(value) {
        this.updateFilter({ search: value })
        if (!this.awaitingSearch) {
          setTimeout(() => {
            this.updateNewsItems()
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
    }
  },
  methods: {
    ...mapGetters(['getItemCount']),
    ...mapGetters('assess', ['getScopeFilterList']),
    ...mapActions('assess', ['updateNewsItems']),
    ...mapActions('filter', [
      'setScope',
      'setFilter',
      'setSort',
      'setLimit',
      'setOffset',
      'updateFilter'
    ]),
    ...mapGetters('filter', ['getNewsItemsFilter'])
  },
  mounted() {
    console.debug('loaded with query', this.query)
  },
  watch: {}
}
</script>
