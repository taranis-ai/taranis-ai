<template>
  <div class="article-source-icon">
    <v-tooltip activator="parent" class="mr-5" :text="source?.name" />
    <img
      v-if="icon"
      :src="'data:image/png;base64,' + icon"
      :alt="source?.name"
      height="30"
    />
    <v-icon v-else :icon="typeIcon" />
  </div>
</template>

<script>
import { getSourceInfo } from '@/utils/helpers.js'
import { computed } from 'vue'

export default {
  name: 'SourceInfo',
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const source = computed(() => {
      return props.newsItem
        ? getSourceInfo(props.newsItem.osint_source_id)
        : null
    })

    const icon = computed(() => {
      return source.value?.icon
    })

    const typeIcon = computed(() => {
      return source.value?.type === 'rss_collector'
        ? 'mdi-rss'
        : source.value?.type === 'web_collector'
          ? 'mdi-code-block-tags'
          : 'mdi-note-edit-outline'
    })

    return {
      source,
      icon,
      typeIcon
    }
  }
}
</script>

<style scoped>
.article-source-icon {
  width: 30px;
  height: 30px;
  max-width: 30px;
  max-height: 30px;
  overflow: hidden;
  border-radius: 7px;
}
</style>
