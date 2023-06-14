<template>
  <v-container v-if="story" fluid style="min-height: 100vh">
    <card-story :story="story" :detail-view="true" />
  </v-container>
</template>

<script>
import { getNewsItemAggregate } from '@/api/assess'
import CardStory from '@/components/assess/CardStory.vue'

export default {
  name: 'StoryView',
  components: {
    CardStory
  },
  data: () => ({
    story: null
  }),
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
