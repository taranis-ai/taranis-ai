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
      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="pb-0">
          <h4>scope</h4>
        </v-col>

        <v-col cols="12" class="pt-0">
          <v-select
            v-model="scope"
            :items="getScopeFilterList()"
            item-text="title"
            item-value="id"
            label="Sources"
            solo
          ></v-select>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <!-- search -->
      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>search</h4>
        </v-col>

        <v-col cols="12">
          <search-field v-model="searchQuery" />
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <!-- filter results -->
      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>filter results</h4>
        </v-col>

        <!-- time tags -->
        <v-col cols="12" class="pb-0">
          <date-chips
            v-model="filter.range"
            @input="filter.range = []"
          />
        </v-col>

        <!-- date picker
        <v-col cols="12">
          <date-range v-model="filter.date" />
        </v-col> -->

        <!-- tags -->
        <v-col cols="10" class="pr-0">
          <tag-filter v-model="filter.tags" :items="tagList" />
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>only show</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-selectList
            v-model="filterAttributeSelections"
            :items="filterAttributeOptions"
          />
        </v-col>
      </v-row>

      <v-divider class="mt-2 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-5 pb-5">
        <v-col cols="12" class="py-0">
          <h4>sort by</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="order.selected" :items="orderOptions" />
        </v-col>
      </v-row>
    </v-container>
  </v-navigation-drawer>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex'
import searchField from '@/components/_subcomponents/searchField'
import dateChips from '@/components/_subcomponents/dateChips'
import tagFilter from '@/components/_subcomponents/tagFilter'
import filterSelectList from '@/components/_subcomponents/filterSelectList'
import filterSortList from '@/components/_subcomponents/filterSortList'

export default {
  name: 'AssessNav',
  components: {
    searchField,
    dateChips,
    tagFilter,
    filterSelectList,
    filterSortList
  },
  data: () => ({
    searchQuery: '',
    awaitingSearch: false,
    filterAttributeSelections: {},
    filterAttributeOptions: [
      { type: 'unread', label: 'unread', icon: '$awakeUnread' },
      {
        type: 'important',
        label: 'important',
        icon: '$awakeImportant'
      },
      {
        type: 'shared',
        label: 'items in reports',
        icon: '$awakeShareOutline'
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
        type: 'publishedDate',
        direction: 'desc'
      },
      {
        label: 'relevance',
        icon: '$awakeRelated',
        type: 'relevanceScore',
        direction: ''
      }
    ],
    tagList: [
      'State',
      'Cyberwar',
      'Threat',
      'DDoS',
      'Vulnerability',
      'Java',
      'CVE',
      'OT/CPS',
      'Python',
      'Privacy',
      'Social',
      'APT',
      'MitM'
    ]
  }),
  computed: {
    ...mapState('filter', {
      scopeState: (state) => state.scope,
      filter: (state) => state.newsItemsFilter,
      order: (state) => state.newsItemsOrder
    }),
    ...mapState(['drawerVisible']),
    scope: {
      get () { return this.scopeState },
      set (value) { this.updateScope(value) }
    }

    // ...mapState('filter', ['newsItemsFilter'])
    // getData () {
    //   return this.$store.getters.getDashboardData
    // }
  },
  methods: {
    ...mapGetters('dashboard', [
      'getStorieSelectionList',
      'getSharingSetSelectionList'
    ]),
    ...mapGetters('assess', [
      'getScopeFilterList'
    ]),
    ...mapActions('assess', [
      'updateNewsItems'
    ]),
    ...mapActions('filter', ['setScope', 'setFilter', 'setOrder']),
    ...mapGetters('filter', ['getNewsItemsFilter']),
    updateScope (scope) {
      this.setScope(scope)
      this.updateNewsItems()
    }
  },
  created () {
  },
  beforeDestroy () {
  },
  watch: {
    searchQuery: function () {
      if (!this.awaitingSearch) {
        setTimeout(() => {
          this.filter.search = this.searchQuery
          this.awaitingSearch = false
        }, 500)
      }

      this.awaitingSearch = true
    }
  }
}
</script>
