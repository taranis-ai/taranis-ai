<template>
  <div>
    <ViewLayout>
      <template v-slot:panel>
        <v-expand-transition style="width: 100%">
          <story-header-assess
            v-if="showStoryHeader"
            :story="showStoryHeader"
          />
        </v-expand-transition>

      </template>
      <template v-slot:content>
        <AssessContent/>
      </template>
    </ViewLayout>
  </div>
</template>

<script>
import ViewLayout from '@/components/layouts/ViewLayout'
import AssessContent from '@/components/assess/AssessContent'
import StoryHeaderAssess from '@/components/assess/StoryHeaderAssess'
// import SharingSetHeaderAssess from '@/components/assess/SharingSetHeaderAssess'

import KeyboardMixin from '../../assets/keyboard_mixin'

import { mapState, mapGetters, mapActions } from 'vuex'

export default {
  name: 'Assess',
  components: {
    ViewLayout,
    AssessContent,
    StoryHeaderAssess
  },
  mixins: [KeyboardMixin('assess')],
  data: () => ({
  }),
  computed: {
    ...mapState('filter', {
      scope: (state) => state.newsItemsFilter.scope,
      filter: (state) => state.newsItemsFilter.filter,
      order: (state) => state.newsItemsFilter.order
    }),

    showStoryHeader () {
      return (this.scope === 'CHECK_IF_STORY')
    }
  },
  methods: {
    ...mapActions('filter', ['resetNewsItemsFilter']),
    ...mapGetters('dashboard', ['getStoryById']),
    ...mapActions('assess', ['updateNewsItems',
      'updateOSINTSourceGroupsList',
      'updateOSINTSources'
    ])
  },
  created () {
    console.log('update SourceList')
    this.updateOSINTSourceGroupsList()
    this.updateOSINTSources()
    this.resetNewsItemsFilter()
    this.updateNewsItems()
  }
}
</script>
