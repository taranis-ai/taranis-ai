<template>
  <iframe :src="targetUrl" :title="title" class="frontend-iframe"></iframe>
</template>

<script>
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'FrontendProxy',
  props: {
    title: {
      type: String,
      default: 'Frontend'
    },
    targetUrl: {
      type: String,
      required: true
    }
  },
  setup() {
    const mainStore = useMainStore()

    mainStore.resetItemCount()
  }
}
</script>
