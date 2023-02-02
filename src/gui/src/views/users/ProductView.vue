<template>
  <v-container fluid style="min-height: 100vh">
    <story-detail :story="story" />
  </v-container>
</template>

<script>
import { getNewsItemAggregate } from '@/api/assess'
import StoryDetail from '@/components/assess/StoryDetail'

export default {
  name: 'ProductView',
  data: () => ({
    story: {}
  }),
  components: {
    StoryDetail
  },
  async created() {
    this.story = await this.loadStories()
  },
  methods: {
    async loadStories() {
      if (this.$route.params.id) {
        return await getNewsItemAggregate(this.$route.params.id).then((response) => {
          return response.data
        })
      }
    }
  }
}
</script>
