<template>
  <v-container v-if="story" fluid>
    <card-story :story="story" :detail-view="true" />
    <assess-selection-toolbar />
  </v-container>
  <not-found-card v-else :item-id="storyId" item-type="Story" />
</template>

<script>
import { ref, onBeforeMount } from 'vue'
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

    const story = ref()

    onBeforeMount(async () => {
      await assessStore.updateOSINTSources()
      story.value = await assessStore.getStoryByID(props.storyId)
    })

    return {
      story
    }
  }
}
</script>
