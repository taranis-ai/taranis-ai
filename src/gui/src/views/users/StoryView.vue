<template>
  <v-container v-if="story" fluid>
    <card-story :story="story" :detail-view="true" />
    <assess-selection-toolbar v-show="activeSelection" />
  </v-container>
  <not-found-card v-else :item-id="story_id" item-type="Story" />
</template>

<script>
import { computed, onMounted } from 'vue'
import CardStory from '@/components/assess/CardStory.vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAssessStore } from '@/stores/AssessStore'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'
import NotFoundCard from '@/components/common/NotFoundCard.vue'

export default {
  name: 'StoryView',
  components: {
    CardStory,
    NotFoundCard,
    AssessSelectionToolbar
  },
  setup() {
    const assessStore = useAssessStore()
    const { activeSelection } = storeToRefs(assessStore)

    const route = useRoute()
    const story_id = route.params.id

    const story = computed(() => {
      return assessStore.stories.items.find((item) => item.id == story_id)
    })

    const loadStories = async () => {
      if (story_id) {
        assessStore.updateStoryByID(story_id)
      }
    }

    onMounted( async () => {
      const assessStore = useAssessStore()
      assessStore.updateOSINTSources()
      loadStories()
    })

    return {
      story,
      story_id,
      activeSelection
    }
  }
}
</script>
