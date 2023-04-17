<template>
  <v-container fluid style="min-height: 100vh" v-if="story">
    <card-story :story="story" :detailView="true" />
  </v-container>
</template>

<script>
import { getNewsItemAggregate } from '@/api/assess'
import CardStory from '@/components/assess/CardStory'

export default {
  name: 'StoryView',
  data: () => ({
    story: null
  }),
  components: {
    CardStory
  },
  async created() {
    this.story = await this.loadStories()
  },
  methods: {
    async loadStories() {
      if (this.$route.params.id) {
        return await getNewsItemAggregate(this.$route.params.id).then(
          (response) => {
            return response.data
          }
        )
      }
    }
  }
}
</script>
