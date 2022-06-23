<template>
  <smooth-scrollbar>
    <v-container class="pa-0">
      <!-- scope -->
      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="pb-0">
          <h4>scope</h4>
        </v-col>

        <v-col cols="12">
          <dropdown-selection
            v-model="scope.topics"
            :items="getTopicSelectionList()"
            label="Topics"
            placeholder="all Topics"
            @input="updateQuery()"
          />
        </v-col>

        <v-col cols="12" class="pt-0">
          <dropdown-selection
            v-model="scope.sharingSets"
            :items="getSharingSetSelectionList()"
            label="Sharing Sets"
            placeholder="all Sharing Sets"
            @input="updateQuery()"
          />
        </v-col>

        <v-col cols="12" class="pt-0">
          <dropdown-selection
            v-model="scope.sources"
            :items="sourcesList"
            label="Sources"
            placeholder="all Sources"
            @input="updateScope()"
          />
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
            v-model="filter.date.selected"
            @input="filter.date.range = []"
          />
        </v-col>

        <!-- date picker -->
        <v-col cols="12">
          <date-range v-model="filter.date" />
        </v-col>

        <!-- tags -->
        <v-col cols="10" class="pr-0">
          <tag-filter v-model="filter.tags.selected" :items="tagList" />
        </v-col>
        <v-col cols="2" class="pl-1 d-flex tags-logic-operator">
          <logical-and v-model="filter.tags.andOperator" />
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>only show</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-selectList
            v-model="filter.attributes.selected"
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
  </smooth-scrollbar>
</template>

<script>
import { mapState, mapGetters, mapActions } from 'vuex'
import searchField from '@/components/_subcomponents/searchField'
import dateChips from '@/components/_subcomponents/dateChips'
import dateRange from '@/components/_subcomponents/dateRange'
import tagFilter from '@/components/_subcomponents/tagFilter'
import logicalAnd from '@/components/_subcomponents/logicalAnd'
import filterSelectList from '@/components/_subcomponents/filterSelectList'
import filterSortList from '@/components/_subcomponents/filterSortList'
import dropdownSelection from '@/components/_subcomponents/dropdownSelection'

export default {
  name: 'AssessNav',
  components: {
    searchField,
    dateChips,
    dateRange,
    tagFilter,
    logicalAnd,
    filterSelectList,
    filterSortList,
    dropdownSelection
  },
  data: () => ({
    searchQuery: '',
    awaitingSearch: false,
    filterAttributeOptions: [
      { type: 'unread', label: 'unread', icon: '$awakeUnread' },
      {
        type: 'important',
        label: 'tagged as important',
        icon: '$awakeImportant'
      },
      {
        type: 'shared',
        label: 'items in sharing set',
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
    ],
    sourcesList: []

  }),
  computed: {
    ...mapState('filter', {
      scope: (state) => state.newsItemsFilter.scope,
      filter: (state) => state.newsItemsFilter.filter,
      order: (state) => state.newsItemsFilter.order
    }),
    // ...mapState('filter', ['newsItemsFilter'])
    // getData () {
    //   return this.$store.getters.getDashboardData
    // }
  },
  methods: {
    ...mapGetters('dashboard', [
      'getTopicSelectionList',
      'getSharingSetSelectionList'
    ]),
    ...mapGetters('assess', [
      'getOSINTSourceGroupList'
    ]),
    ...mapActions('assess', [
      'updateNewsItemsByGroup'
    ]),

    updateSourcesList () {
      this.sourcesList = this.getSourceNames(this.getOSINTSourceGroupList())
      console.log(this.sourcesList)
    },
    updateScope () {
      var filter
      this.scope.sources.forEach(function(source) {
        filter = { 'group_id': source.id, 
          'data': { 'offset': 10, 'limit': 15, 'filter': { 
          'search': '',
          'sort': '',
          'range': '',
          'in_analyze': false,
          'relevant': false,
          'important': false
        }}}
      })
      if (filter) {
        this.updateNewsItemsByGroup(filter)
      }
    },

    updateQuery () {
      if (this.scope.topics.length === 1) {
        this.$router.push({ query: { topic: this.scope.topics[0].id } })
      } else if (this.scope.sharingSets.length === 1) {
        this.$router.push({
          query: { topic: this.scope.sharingSets[0].id }
        })
      }
    },
    getSourceNames (data) {
      if (!data.items) {
        return []
      }
      return data.items.map(value => ({ id: value.id, title: value.name }))
    }
  },
  created () {
  this.updateSourcesList()
  this.unsubscribe = this.$store.subscribe((mutation, state) => {
    if (mutation.type === 'assess/setOSINTSourceGroups') {
      this.updateSourcesList()
    }
  });
  },

  beforeDestroy () {
    this.unsubscribe();
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
