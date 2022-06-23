<template>
  <smooth-scrollbar>
    <v-container class="pa-0">
      <!-- search -->
      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="pb-0">
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
          <filter-select-list
            v-model="filter.attributes.selected"
            :items="filterAttributeOptions"
          />
        </v-col>
      </v-row>

      <v-divider class="mt-2 mb-0"></v-divider>

      <v-row class="my-3 mr-0 px-5">
        <v-col cols="12" class="py-0">
          <h4>sort by</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="order.selected" :items="orderOptions" />
        </v-col>
      </v-row>

      <v-divider class="mt-1 mb-0"></v-divider>

      <v-row class="mt-1 mr-0 px-5 pb-10">
        <v-col cols="12" class="py-0">
          <v-checkbox
            v-model="order.keepPinned"
            dense
            hide-details
            label="Pinned always on top"
          ></v-checkbox>
        </v-col>
      </v-row>
    </v-container>
  </smooth-scrollbar>
</template>

<script>
import { mapState } from 'vuex'
import searchField from '@/components/_subcomponents/searchField'
import dateChips from '@/components/_subcomponents/dateChips'
import dateRange from '@/components/_subcomponents/dateRange'
import tagFilter from '@/components/_subcomponents/tagFilter'
import logicalAnd from '@/components/_subcomponents/logicalAnd'
import filterSelectList from '@/components/_subcomponents/filterSelectList'
import filterSortList from '@/components/_subcomponents/filterSortList'

export default {
  name: 'DashboardNav',
  components: {
    searchField,
    dateChips,
    dateRange,
    tagFilter,
    logicalAnd,
    filterSelectList,
    filterSortList
  },
  data: () => ({
    filterAttributeOptions: [
      { type: 'active', label: 'active topics', icon: 'mdi-message-outline' },
      { type: 'pinned', label: 'pinned topics', icon: '$awakePin' },
      { type: 'hot', label: 'hot topics', icon: 'mdi-star-outline' },
      {
        type: 'sharingSets',
        label: 'sharing sets',
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
        label: 'relevance score',
        icon: 'mdi-star-outline',
        type: 'relevanceScore',
        direction: 'desc'
      },
      {
        label: 'last activity',
        icon: 'mdi-calendar-range-outline',
        type: 'lastActivity',
        direction: ''
      },
      {
        label: 'new news items',
        icon: 'mdi-file-outline',
        type: 'newItems',
        direction: ''
      },
      {
        label: 'new comments',
        icon: 'mdi-message-outline',
        type: 'newComments',
        direction: ''
      },
      {
        label: 'upvotes',
        icon: 'mdi-arrow-up-circle-outline',
        type: 'upvotes',
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
      filter: (state) => state.topicsFilter.filter,
      order: (state) => state.topicsFilter.order
    })
  }
}
</script>
