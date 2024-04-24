<template>
  <StoryEdit v-if="story" :story-prop="story" />
</template>

<script>
import StoryEdit from '@/components/assess/StoryEdit.vue'
import { ref, onBeforeMount } from 'vue'
import { getStory } from '@/api/assess'

export default {
  name: 'StoryEditView',
  components: {
    StoryEdit
  },
  props: {
    storyId: {
      type: String,
      required: true
    }
  },
  setup(props) {
    const story = ref(null)

    onBeforeMount(async () => {
      const response = await getStory(props.storyId)
      story.value = response.data
    })

    return {
      story
    }
  }
}
</script>
