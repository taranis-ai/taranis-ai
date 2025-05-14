<template>
  <StoryEdit v-if="story" :story-prop="story" />
  <not-found-card v-else :item-id="storyId" item-type="Story" />
</template>

<script>
import StoryEdit from '@/components/assess/StoryEdit.vue'
import NotFoundCard from '@/components/common/NotFoundCard.vue'
import { onBeforeMount, ref } from 'vue'
import { useAssessStore } from '@/stores/AssessStore'

export default {
  name: 'StoryEditView',
  components: {
    StoryEdit,
    NotFoundCard
  },
  props: {
    storyId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const assessStore = useAssessStore()
    const story = ref()

    onBeforeMount(async () => {
      story.value = await assessStore.getStoryByID(props.storyId)
    })

    return {
      story
    }
  }
}
</script>
