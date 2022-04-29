<template>
  <v-col class="overflow-hidden">
    <v-container fluid>
      <transition name="empty-list-transition" mode="out-in">
        <v-row v-if="!filteredNewsItems.length">
          <v-col cols="12" class="empty-list-notification">
            <v-icon x-large> mdi-circle-off-outline </v-icon>
            <span v-if="getNewsItems().length">
              The currently selected filters do not yield any results. Try
              changing the filters.
            </span>
            <span v-else> No elements to display. </span>
          </v-col>
        </v-row>

        <transition-group
          name="news-items-grid"
          tag="div"
          class="row d-flex align-stretch row--dense topics-grid-container"
          v-else
          appear
        >
          <card-news-item
            v-for="(newsItem, index) in filteredNewsItems"
            :key="newsItem.id"
            :newsItem="newsItem"
            :position="index"
            @deleteItem="deleteItem"
          ></card-news-item>
        </transition-group>
      </transition>
    </v-container>

    <v-expand-transition>
      <assess-selection-toolbar
        class="px-1 pt-2 pb-3"
        v-if="activeSelection"
        :selection="getNewsItemsSelection()"
      ></assess-selection-toolbar>
    </v-expand-transition>
  </v-col>
</template>

<script>
import CardNewsItem from '@/components/common/card/CardNewsItem'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar'

import { mapState, mapGetters, mapActions } from 'vuex'
import { filterSearch, filterDateRange, filterTags } from '@/utils/ListFilters'
import moment from 'moment'

export default {
  name: 'AssessContent',
  components: {
    CardNewsItem,
    AssessSelectionToolbar
  },
  props: {
    // topic: {}
    // analyze_selector: Boolean,
    // selection: Array,
    // selfID: String,
    // data_set: String
  },
  data: () => ({
    newsItems_loaded: false
  }),
  methods: {
    ...mapActions('assess', ['deleteNewsItem']),
    ...mapGetters('assess', [
      'getNewsItems',
      'getNewsItemsSelection',
      'getNewsItemsByTopicId',
      'getNewsItemsByTopicList'
    ]),

    // infiniteScrolling (entries, observer, isIntersecting) {
    //   if (this.newsItems_loaded && isIntersecting) {
    //     this.updateData(true, false)
    //   }
    // }

    // showItemDetail (news_item) {
    //   this.$root.$emit('change-state', 'SHOW_ITEM')
    //   this.$refs.newsItemDetail.open(news_item)
    // },

    // updateData (append, reload_all) {
    //   this.newsItems_loaded = false

    //   if (append === false) {
    //     this.newsItems = []
    //   }

    //   let offset = this.newsItems.length
    //   let limit = 20
    //   if (reload_all) {
    //     offset = 0
    //     if (this.newsItems.length > limit) {
    //       limit = this.newsItems.length
    //     }
    //     this.newsItems = []
    //   }

    //   let group = ''

    //   if (this.analyze_selector) {
    //     group = this.$store.getters.getCurrentGroup
    //   } else {
    //     if (window.location.pathname.includes('/group/')) {
    //       const i = window.location.pathname.indexOf('/group/')
    //       const len = window.location.pathname.length
    //       group = window.location.pathname.substring(i + 7, len)
    //       this.$store.dispatch('changeCurrentGroup', group)
    //     }
    //   }

    //   this.$store
    //     .dispatch('getNewsItemsByGroup', {
    //       group_id: group,
    //       data: {
    //         filter: this.news_items_filter,
    //         offset: offset,
    //         limit: limit
    //       }
    //     })
    //     .then(() => {
    //       this.newsItems = this.newsItems.concat(
    //         this.$store.getters.getNewsItems.items
    //       )
    //       this.$emit(
    //         'new-data-loaded',
    //         this.$store.getters.getNewsItems.total_count
    //       )
    //       setTimeout(() => {
    //         this.$emit('card-items-reindex')
    //       }, 200)
    //       setTimeout(() => {
    //         this.newsItems_loaded = true
    //       }, 1000)
    //     })
    // },

    // checkFocus (pos) {
    //   this.$root.$emit('check-focus', pos)
    // },

    // news_items_updated () {
    //   // only update items when not in selection mode
    //   if (!this.activeSelection) {
    //     this.updateData(false, true)
    //   }
    // },

    deleteItem (id) {
      this.deleteNewsItem(id)
    }
  },

  computed: {
    ...mapState('newsItemsFilter', ['filter', 'order']),
    ...mapState('assess', ['newsItems']),

    filteredNewsItems () {
      let filteredData = []
      if (
        this.filter.scope.topics.length &&
        this.filter.scope.sharingSets.length
      ) {
        const scopedData = this.getNewsItemsByTopicList()(
          this.filter.scope.topics
        )

        const sharingSetList = this.filter.scope.sharingSets

        filteredData = scopedData.filter((newsItem) => {
          return newsItem.sharingSets.some(
            (itemSharingSet) =>
              sharingSetList
                .map((sharingSet) => sharingSet.id)
                .indexOf(itemSharingSet) >= 0
          )
        })
      } else if (this.filter.scope.topics.length) {
        filteredData = this.getNewsItemsByTopicList()(this.filter.scope.topics)
      } else if (this.filter.scope.sharingSets.length) {
        filteredData = this.getNewsItemsByTopicList()(
          this.filter.scope.sharingSets
        )
      } else {
        filteredData = this.getNewsItems()
      }

      // ---------------------------------------------------------------------------------------

      filteredData = filteredData.filter((item) => {
        // Only show
        const onlyShowAttr = this.filter.attributes.selected
        if (onlyShowAttr.includes('unread') && item.read) return false
        if (onlyShowAttr.includes('important') && !item.important) return false
        if (onlyShowAttr.includes('shared') && !item.shared) return false
        if (
          onlyShowAttr.includes('selected') &&
          !this.getNewsItemsSelection().includes(item.id)
        ) {
          return false
        }

        // Tags filter
        const tagsResult =
          !this.filter.tags.selected.length ||
          filterTags(
            item.tags,
            this.filter.tags.selected,
            this.filter.tags.andOperator
          )
        if (!tagsResult) return false

        // Date filter
        const dateResult =
          this.filter.date.selected === 'all' ||
          filterDateRange(
            item.published,
            this.filter.date.selected,
            this.filter.date.range
          )
        if (!dateResult) return false

        // Search filter
        const searchResult =
          !this.filter.search ||
          filterSearch([item.title, item.summary], this.filter.search)
        if (!searchResult) return false

        return true
      })

      // ---------------------------------------------------------------------------------------

      // // SEARCH
      // filteredData = filteredData.filter((item) => {
      //   return (
      //     !this.filter.search ||
      //     filterSearch([item.title, item.summary], this.filter.search)
      //   )
      // })

      // // DATE
      // filteredData = filteredData.filter((item) => {
      //   return (
      //     this.filter.date.selected === 'all' ||
      //     filterDateRange(
      //       item.published,
      //       this.filter.date.selected,
      //       this.filter.date.range
      //     )
      //   )
      // })

      // // TAGS
      // filteredData = filteredData.filter((item) => {
      //   return (
      //     this.filter.tags.selected.includes('all') ||
      //     filterTags(
      //       item.tags,
      //       this.filter.tags.selected,
      //       this.filter.tags.andOperator
      //     )
      //   )
      // })

      // ONLY SHOW
      // this.filter.attributes.selected.forEach((type) => {
      //   filteredData = filteredData.filter((item) => {
      //     switch (type) {
      //       case 'unread':
      //         return !item.read
      //       case 'important':
      //         return item.important
      //       case 'shared':
      //         return item.shared
      //       case 'selected':
      //         return item.selected
      //     }
      //   })
      // })

      // SORTING
      filteredData.sort((x, y) => {
        const directionModifier =
          this.order.selected.direction === 'asc' ? 1 : -1

        if (x === y) return 0

        switch (this.order.selected.type) {
          case 'relevanceScore':
            return x.relevanceScore < y.relevanceScore
              ? -1 * directionModifier
              : 1 * directionModifier
          case 'publishedDate':
            return (
              (moment(x.published, 'DD/MM/YYYY hh:mm:ss') -
                moment(y.published, 'DD/MM/YYYY hh:mm:ss')) *
              directionModifier
            )
        }
      })

      this.$store.dispatch('updateItemCount', {
        total: this.newsItems.length,
        filtered: filteredData.length
      })

      return filteredData
    },

    activeSelection () {
      return this.getNewsItemsSelection().length > 0
    }
  },

  mounted () {
    // this.$root.$on('news-items-updated', this.news_items_updated)
    // this.$root.$on('force-reindex', this.forceReindex)
  }

  // beforeDestroy () {
  //   this.$root.$off('news-items-updated', this.news_items_updated)
  // }
}
</script>
