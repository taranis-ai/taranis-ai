<template>
  <v-col>
    <v-container fluid>
      <transition name="empty-list-transition" mode="out-in">
        <v-row v-if="!filteredTopics.length">
          <v-col cols="12" class="empty-list-notification">
            <v-icon x-large> mdi-circle-off-outline </v-icon>
            <span v-if="this.topics.length">
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
            <card-topic :topic="topic"></card-topic>
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

    <v-container class="d-none">
      <v-row no-gutters>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="white"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
                <wordcloud
                  :data="tagCloud"
                  nameKey="word"
                  valueKey="wordQuantity"
                  :color="myColors"
                  :showTooltip="false"
                  :rotate="myRotate"
                  :fontSize="fontSize"
                  :wordClick="wordClickHandler"
                >
                </wordcloud>
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Assess</div>
                <div class="subheading grey--text">
                  Tagcloud for latest collected news items.
                </div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2"> mdi-email-multiple </v-icon>
                <span class="caption grey--text"
                  >There are <strong>{{ getData.totalNewsItems }}</strong> total
                  Assess items.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="6" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-card-text class="pt-0">
                <div class="title mb-2">Publish</div>
                <!--<div class="subheading grey&#45;&#45;text">Number of pending analyses per hour</div>-->
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="orange">
                  mdi-email-check-outline
                </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.totalProducts }}</b> products ready
                  for publications.</span
                >
                <v-divider inset></v-divider>
              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="4" class="pa-2 mb-4">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Analyze</div>
                <div class="subheading grey--text">Status of report items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2"> mdi-account </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.reportItemsCompleted }}</b> completed
                  analyses.</span
                >
                <v-divider inset></v-divider>
                <v-icon class="mr-2" color="grey">
                  mdi-account-question-outline
                </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.reportItemsInProgress }}</b> pending
                  analyses.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Collect</div>
                <div class="subheading grey--text">
                  Collectors activity status
                </div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="green">
                  mdi-lightbulb-off-outline
                </v-icon>
                <span class="caption grey--text"
                  >Collectors are pending at the moment.</span
                >
                <v-divider inset></v-divider>

                <v-icon class="mr-2"> mdi-clock-check-outline </v-icon>
                <span class="caption grey--text"
                  >Last successful run ended at
                  <b>{{ getData.latestCollected }}</b></span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
        <v-col cols="4" class="pa-2 mb-8">
          <template>
            <v-card class="mt-4 mx-auto" max-width="100%">
              <v-sheet
                class="v-sheet--offset mx-auto"
                color="cyan"
                elevation="4"
                max-width="calc(100% - 32px)"
              >
              </v-sheet>

              <v-card-text class="pt-0">
                <div class="title mb-2">Database</div>
                <div class="subheading grey--text">Number of live items</div>
                <v-divider class="my-2"></v-divider>
                <v-icon class="mr-2" color="blue"> mdi-database </v-icon>
                <span class="caption grey--text"
                  >There are <b>{{ getData.totalDatabaseItems }}</b> live
                  items.</span
                >
                <v-divider inset></v-divider>

                <v-icon class="mr-2"> mdi-database-check </v-icon>
                <span class="caption grey--text"
                  >There are <b>0</b> archived items.</span
                >
              </v-card-text>
            </v-card>
          </template>
        </v-col>
      </v-row>
    </v-container>
  </v-col>
</template>

<script>
import wordcloud from 'vue-wordcloud'
import DashboardSelectionToolbar from '@/components/dashboard/DashboardSelectionToolbar'
import CardTopic from '@/components/common/card/CardTopic'

import { mapState, mapGetters, mapActions } from 'vuex'
import { filterSearch, filterDateRange, filterTags } from '@/utils/ListFilters'
import moment from 'moment'

export default {
  name: 'DashboardContent',
  components: {
    wordcloud,
    CardTopic,
    DashboardSelectionToolbar
  },
  data: () => ({
    items: [1, 2, 3, 4, 5, 6, 7, 8, 9],
    myColors: ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef'],
    myRotate: { from: 0, to: 0, numOfOrientation: 0 },
    fontSize: [14, 40],
    tagCloud: [],
    labels: ['12am', '3am', '6am', '9am', '12pm', '3pm', '6pm', '9pm'],
    value: [200, 675, 410, 390, 310, 460, 250, 240],
    replacement: [],
    filterList: {},
    selection: []
  }),
  methods: {
    ...mapActions('dashboard', ['updateTopics', 'unselectAllTopics']),
    ...mapGetters('dashboard', ['getTopics', 'getTopicSelection']),

    getData () {
      return this.$store.getters.getDashboardData
    },
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
      //   this.$store.dispatch('getAllDashboardData').then(() => {
      //     this.tagCloud = this.$store.getters.getDashboardData.tagCloud
      //   })
    }
  },
  computed: {
    ...mapState('topicsFilter', ['filter', 'order']),

    ...mapState('dashboard', ['topics', 'topicSelection']),

    filteredTopics () {
      let filteredData = this.getTopics()

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
  mounted () {
    this.refreshTagCloud()
    this.unselectAllTopics()

    setInterval(
      function () {
        this.refreshTagCloud()
      }.bind(this),
      600000
    )
  }
}
</script>
