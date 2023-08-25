<template>
  <v-container v-if="story" fluid style="min-height: 100vh">
    <card-story
      :story="story"
      :detail-view="true"
      @delete-item="deleteNewsItem(story.id)"
    />
  </v-container>
</template>

<script>
import { computed, onMounted } from 'vue'
import CardStory from '@/components/assess/CardStory.vue'
import { useRoute } from 'vue-router'
import { useAssessStore } from '@/stores/AssessStore'

export default {
  name: 'StoryView',
  components: {
    CardStory
  },
  setup() {
    const assessStore = useAssessStore()
    const route = useRoute()

    console.debug(assessStore.newsItems.items)
    const story = computed(() => {
      return assessStore.newsItems.items.find(
        (item) => item.id == route.params.id
      )
    })

    const loadStories = async () => {
      if (route.params.id) {
        assessStore.updateNewsItemByID(route.params.id)
      }
    }

    const deleteNewsItem = (id) => {
      assessStore.removeNewsItemByID(id)
    }

    onMounted(() => {
      loadStories()
    })

    return {
      story,
      deleteNewsItem
    }
  }
}
</script>
