<template>
  <v-container v-if="story" fluid style="min-height: 100vh">
    <card-story
      :story="story"
      :detail-view="true"
      @delete-item="deleteNewsItem(story.id)"
    />
    <assess-selection-toolbar v-if="activeSelection" />
  </v-container>
</template>

<script>
import { computed, onMounted } from 'vue'
import CardStory from '@/components/assess/CardStory.vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAssessStore } from '@/stores/AssessStore'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'

export default {
  name: 'StoryView',
  components: {
    CardStory,
    AssessSelectionToolbar
  },
  setup() {
    const assessStore = useAssessStore()
    const { activeSelection } = storeToRefs(assessStore)

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
      activeSelection,
      deleteNewsItem
    }
  }
}
</script>
