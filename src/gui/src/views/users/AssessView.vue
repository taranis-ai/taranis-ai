<template>
  <div>
    <ViewLayout>
      <template v-slot:panel>
        <!-- Display Topic Header -->
        <v-expand-transition style="width: 100%">
          <topic-header-assess
            v-if="topicView"
            :topic="getTopicById()(scope.topics[0].id)"
          />
        </v-expand-transition>

        <!-- Display Sharing Set Header Header -->
        <v-expand-transition style="width: 100%">
          <sharing-set-header-assess
            v-if="sharingSetView"
            :topic="getTopicById()(scope.sharingSets[0].id)"
          />
        </v-expand-transition>
      </template>
      <template v-slot:content>
        <!-- Load News Items -->
        <AssessContent
          :topicView="topicView"
          :sharingSetView="sharingSetView"
          :itemsToLoad="itemsToLoad"
          ref="contentData"
        />
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
  data: () => ({
    itemsToLoad: 0
  }),
  computed: {
    ...mapState('filter', {
      scope: (state) => state.newsItemsFilter.scope,
      filter: (state) => state.newsItemsFilter.filter,
      order: (state) => state.newsItemsFilter.order
    }),

    topicView () {
      return this.scope.topics.length === 1
    },

    sharingSetView () {
      return (
        this.scope.topics.length === 0 && this.scope.sharingSets.length === 1
      )
    }
  },
  methods: {
    ...mapActions('filter', ['resetNewsItemsFilter']),
    ...mapGetters('dashboard', ['getTopicById']),
    ...mapActions('assess', ['updateNewsItems',
      'updateOSINTSourceGroupsList',
      'updateOSINTSources'
    ])
  },
  created () {
    console.log('update SourceLise')
    this.updateOSINTSourceGroupsList()
    this.updateOSINTSources()

    // Clear all news items filter
    this.resetNewsItemsFilter()

    // If topic is given in query set it as filter
    const topicId = parseInt(this.$route.query.topic)
    if (topicId) {
      const topic = this.getTopicById()(topicId)
      this.itemsToLoad = topic.items.total
      if (topic) {
        if (topic.isSharingSet) {
          this.scope.sharingSets = [{ id: topicId, title: topic.title }]
          this.scope.topics = []
        } else {
          this.scope.sharingSets = []
          this.scope.topics = [{ id: topicId, title: topic.title }]
        }
      }
    }
  }
}
</script>
