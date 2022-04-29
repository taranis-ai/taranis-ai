<template>
  <div>
    <ViewLayout>
      <template v-slot:panel>
        <!-- Display Topic Header -->
        <v-expand-transition style="width: 100%">
          <topic-header-assess v-if="showTopicHeader" />
        </v-expand-transition>

        <!-- Display Sharing Set Header Header -->
        <v-expand-transition style="width: 100%">
          <sharing-set-header-assess v-if="showSharingSetHeader" />
        </v-expand-transition>
      </template>
      <template v-slot:content>
        <!-- Load News Items -->
        <AssessContent />
      </template>
    </ViewLayout>
  </div>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import AssessContent from '@/components/assess/AssessContent'
import TopicHeaderAssess from '@/components/assess/TopicHeaderAssess'
import SharingSetHeaderAssess from '@/components/assess/SharingSetHeaderAssess'

import KeyboardMixin from '../../assets/keyboard_mixin'

import { mapState, mapGetters, mapActions } from 'vuex'

export default {
  name: 'Assess',
  components: {
    ViewLayout,
    AssessContent,
    TopicHeaderAssess,
    SharingSetHeaderAssess
  },
  mixins: [KeyboardMixin('assess')],
  computed: {
    ...mapState('newsItemsFilter', ['filter']),

    showTopicHeader () {
      return this.filter.scope.topics.length === 1
    },
    showSharingSetHeader () {
      return (
        this.filter.scope.topics.length !== 1 &&
        this.filter.scope.sharingSets.length === 1
      )
    },

    multiSelectActive () {
      return this.$store.getters.getMultiSelect
    }
  },
  methods: {
    ...mapActions('newsItemsFilter', ['resetNewsItemsFilter']),
    ...mapGetters('dashboard', ['getTopicById'])

    // newDataLoaded (count) {
    //   this.$refs.toolbarFilter.updateDataCount(count)
    // },

    // updateFilter (filter) {
    //   this.$refs.contentData.updateFilter(filter)
    //   this.$store.dispatch('filter', filter)
    //   this.filter = filter
    // },

    // cardReindex () {
    //   this.keyRemaper()

    //   // this scrolls the page all the way up... it should only scroll to the top of the newly-loaded items
    //   // setTimeout( ()=>{
    //   //     this.scrollPos();
    //   // },1 )

    //   if (this.focus) {
    //     this.$refs.contentData.checkFocus(this.pos)
    //   }
    // },

    // firstDialog (action) {
    //   if (action === 'push') {
    //     this.dialog_stack++
    //   } else {
    //     this.dialog_stack--
    //   }
    //   if (this.dialog_stack <= 0) {
    //     this.isItemOpen = false
    //     this.dialog_stack = 0
    //   } else {
    //     this.isItemOpen = true
    //   }
    // }
  },
  watch: {
    // $route () {
    //   this.$refs.contentData.updateData(false, false)
    // }
  },
  mounted () {
    // if (window.location.pathname.includes('/group/')) {
    //   this.$refs.contentData.updateData(false, false)
    // }

    // this.$root.$on('first-dialog', (action) => {
    //   this.firstDialog(action)
    // })

    // this.$root.$on('clear-cards', () => {
    //   const cards = document.querySelectorAll('.card-item')
    //   cards.forEach((card) => card.remove())
    // })

    // Clear all news items filter
    this.resetNewsItemsFilter()

    // If topic is given in query set it as filter
    const topicId = parseInt(this.$route.query.topic)
    if (topicId) {
      const topic = this.getTopicById()(topicId)
      if (topic) {
        if (topic.isSharingSet) {
          this.filter.scope.sharingSets = [{ id: topicId, title: topic.title }]
          this.filter.scope.topics = []
        } else {
          this.filter.scope.sharingSets = []
          this.filter.scope.topics = [{ id: topicId, title: topic.title }]
        }
      }
    }
  }
}
</script>
