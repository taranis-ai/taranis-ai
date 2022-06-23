<template>
  <v-col>
    <v-container fluid>
      <loader v-if="topicsLoaded.length < topics.length" label="loading topics" />

      <transition name="empty-list-transition" mode="out-in">
        <v-row v-if="!filteredTopics.length">
          <v-col cols="12" class="empty-list-notification">
            <v-icon x-large> mdi-circle-off-outline </v-icon>
            <span v-if="topics.length">
              The currently selected filters do not yield any results. Try
              changing the filters.
            </span>
            <span v-else> No elements to display. </span>
          </v-col>
        </v-row>

        <transition-group
          name="topics-grid"
          tag="div"
          class="row d-flex align-stretch row--dense topics-grid-container"
          v-else
          appear
        >
          <v-col
            xs="12"
            sm="6"
            md="4"
            xl="3"
            v-for="topic in filteredTopics"
            :key="topic.id"
          >
            <card-topic
            :topic="topic"
            @init="topicsLoaded.push(topic.id)"
            ></card-topic>
          </v-col>
        </transition-group>
      </transition>
    </v-container>

    <v-expand-transition>
      <dashboard-selection-toolbar
        class="px-1 pt-2 pb-3"
        v-if="activeSelection"
        :selection="getTopicSelection()"
      ></dashboard-selection-toolbar>
    </v-expand-transition>

  </v-col>
</template>

<script>
import wordcloud from 'vue-wordcloud'
import DashboardSelectionToolbar from '@/components/dashboard/DashboardSelectionToolbar'
import CardTopic from '@/components/common/card/CardTopic'
import Loader from '@/components/common/Loader'

import { mapState, mapGetters, mapActions } from 'vuex'
import { filterSearch, filterDateRange, filterTags } from '@/utils/ListFilters'
import moment from 'moment'

export default {
  name: 'DashboardContent',
  components: {
    wordcloud,
    CardTopic,
    DashboardSelectionToolbar,
    Loader
  },
  data: () => ({
    topics: [],
    topicsLoaded: []
  }),
  methods: {
    ...mapActions('dashboard', ['updateTopics', 'unselectAllTopics']),
    ...mapGetters('dashboard', ['getTopics', 'getTopicSelection']),

    getTopicsData () {
      this.topics = this.getTopics()
    },

    // getData () {
    //   return this.$store.getters.getDashboardData
    // },
    wordClickHandler (name, value, vm) {
      window.console.log('wordClickHandler', name, value, vm)
    },
    refreshTagCloud () {
      // Dummy Tag-Cloud data
      this.tagCloud = [
        { name: 'State', value: 26 },
        { name: 'Cyberwar', value: 19 },
        { name: 'Threat', value: 18 },
        { name: 'DDoS', value: 16 },
        { name: 'Vulnerability', value: 15 },
        { name: 'Java', value: 9 },
        { name: 'CVE', value: 9 },
        { name: 'OT/CPS', value: 9 },
        { name: 'Python', value: 6 }
      ]
    }
  },
  computed: {
    
    ...mapState('filter',
      {
        filter: state => state.topicsFilter.filter,
        order: state => state.topicsFilter.order
      }
    ),

    ...mapState('dashboard', ['topicSelection']),

    filteredTopics () {
      let filteredData = [...this.topics]

      // SEARCH
      if (this.filter.search.length > 2) {
        filteredData = filteredData.filter((item) => {
          return (
            !this.filter.search ||
            filterSearch([item.title, item.summary], this.filter.search)
          )
        })
      }

      // DATE
      filteredData = filteredData.filter((item) => {
        return (
          this.filter.date.selected === 'all' ||
          filterDateRange(
            item.lastActivity,
            this.filter.date.selected,
            this.filter.date.range
          )
        )
      })

      // TAGS
      filteredData = filteredData.filter((item) => {
        return (
          this.filter.tags.selected.includes('all') ||
          filterTags(
            item.tags,
            this.filter.tags.selected,
            this.filter.tags.andOperator
          )
        )
      })

      // ONLY SHOW
      this.filter.attributes.selected.forEach((type) => {
        filteredData = filteredData.filter((item) => {
          switch (type) {
            case 'active':
              return item.comments.new > 0
            case 'pinned':
              return item.pinned
            case 'hot':
              return item.hot
            case 'upvoted':
              return item.votes.up > item.votes.down
            case 'sharingSets':
              return item.isSharingSet
            case 'selected':
              return item.selected
            default:
              return true
          }
        })
      })

      // SORTING
      filteredData.sort((x, y) => {
        const directionModifier =
          this.order.selected.direction === 'asc' ? 1 : -1

        const sorter = function (a, b) {
          return a < b ? -1 * directionModifier : 1 * directionModifier
        }

        if (this.order.keepPinned) {
          if (x.pinned && !y.pinned) return -1
          if (!x.pinned && y.pinned) return 1
        }

        if (x === y) return 0

        switch (this.order.selected.type) {
          case 'relevanceScore':
            return sorter(x.relevanceScore, y.relevanceScore)
          case 'newItems':
            return sorter(x.items.new, y.items.new)
          case 'newComments':
            return sorter(x.comments.new, y.comments.new)
          case 'upvotes':
            return sorter(x.votes.up, y.votes.up)
          case 'lastActivity':
            return (
              (moment(x.lastActivity, 'DD/MM/YYYY hh:mm:ss') -
                moment(y.lastActivity, 'DD/MM/YYYY hh:mm:ss')) *
              directionModifier
            )
        }
      })

      this.$store.dispatch('updateItemCount', {
        total: this.topics.length,
        filtered: filteredData.length
      })

      return filteredData
    },

    activeSelection () {
      return this.topicSelection.length > 0
    }
  },
  created () {
    this.unsubscribe = this.$store.subscribe((mutation, state) => {
      if (mutation.type === 'dashboard/UPDATE_TOPICS') {
        // this.getTopicsData()
        // this.unselectAllTopics()
      }
    });
  },

  beforeDestroy() {
    this.unsubscribe();
  }
}
</script>
