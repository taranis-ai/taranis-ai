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
            v-model="filter.scope.topics"
            :items="getTopicSelectionList()"
            label="Topics"
            placeholder="all Topics"
            @input="updateQuery()"
          />
        </v-col>

        <v-col cols="12" class="pt-0">
          <dropdown-selection
            v-model="filter.scope.sharingSets"
            :items="getSharingSetSelectionList()"
            label="Sharing Sets"
            placeholder="all Sharing Sets"
            @input="updateQuery()"
          />
        </v-col>

        <v-col cols="12" class="pt-0">
          <dropdown-selection
            v-model="filter.scope.sources"
            :items="sourcesList"
            label="Sources"
            placeholder="all Sources"
            @input="updateQuery()"
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
          <search-field v-model="filter.search" />
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
import { mapState, mapGetters } from 'vuex'
import searchField from '@/components/inputs/searchField'
import dateChips from '@/components/inputs/dateChips'
import dateRange from '@/components/inputs/dateRange'
import tagFilter from '@/components/inputs/tagFilter'
import logicalAnd from '@/components/inputs/logicalAnd'
import filterSelectList from '@/components/inputs/filterSelectList'
import filterSortList from '@/components/inputs/filterSortList'
import dropdownSelection from '@/components/inputs/dropdownSelection'

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
    sourcesList: [
      { id: 1, title: 'Source 1' },
      { id: 2, title: 'Source 2' },
      { id: 3, title: 'Source 3' },
      { id: 4, title: 'Source 4' }
    ]
  }),
  computed: {
    ...mapState('newsItemsFilter', ['filter', 'order'])
    // getData () {
    //   return this.$store.getters.getDashboardData
    // }
  },
  methods: {
    ...mapGetters('dashboard', [
      'getTopicSelectionList',
      'getSharingSetSelectionList'
    ]),

    updateQuery () {
      if (this.filter.scope.topics.length === 1) {
        this.$router.push({ query: { topic: this.filter.scope.topics[0].id } })
      } else if (this.filter.scope.sharingSets.length === 1) {
        this.$router.push({
          query: { topic: this.filter.scope.sharingSets[0].id }
        })
      } else {
        this.$router.push({ query: '' })
      }
    }
  }
}
</script>
