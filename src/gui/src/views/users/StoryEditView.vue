<template>
  <StoryEdit v-if="story" :story-prop="story" />
</template>

<script>
import StoryEdit from '@/components/assess/StoryEdit.vue'
import { ref, onBeforeMount } from 'vue'
import { useRoute } from 'vue-router'
import { getStory } from '@/api/assess'

export default {
  name: 'StoryEditView',
  components: {
    StoryEdit
  },
  setup() {
    const route = useRoute()

    const story = ref(null)

    onBeforeMount(async () => {
      const response = await getStory(route.params.id)
      story.value = response.data
    })

    return {
      story
    }
  }
}
</script>
