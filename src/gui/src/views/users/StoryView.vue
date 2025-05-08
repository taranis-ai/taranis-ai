<template>
  <v-container v-if="story" fluid>
    <card-story :story="story" :detail-view="true" />
    <assess-selection-toolbar />
  </v-container>
  <not-found-card v-else :item-id="storyId" item-type="Story" />
</template>

<script>
import { computed, onMounted } from 'vue'
import CardStory from '@/components/assess/CardStory.vue'
import { useAssessStore } from '@/stores/AssessStore'
import AssessSelectionToolbar from '@/components/assess/AssessSelectionToolbar.vue'
import NotFoundCard from '@/components/common/NotFoundCard.vue'
import { storyHotkeys } from '@/utils/hotkeys'

export default {
  name: 'StoryView',
  components: {
    CardStory,
    NotFoundCard,
    AssessSelectionToolbar
  },
  props: {
    storyId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const assessStore = useAssessStore()

    storyHotkeys()

    const story = computed(() => {
      return assessStore.getStoryByID(props.storyId)
    })

    onMounted(async () => {
      assessStore.updateOSINTSources()
    })

    return {
      story
    }
  }
}
</script>
