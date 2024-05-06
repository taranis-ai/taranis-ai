<template>
  <NewsItemEdit :story-id="storyId" />
</template>

<script>
import NewsItemEdit from '@/components/assess/NewsItemEdit.vue'

export default {
  name: 'EnterView',
  components: {
    NewsItemEdit
  },
  props: {
    storyId: {
      type: String,
      default: null,
      required: false
    }
  },
  setup() {}
}
</script>
