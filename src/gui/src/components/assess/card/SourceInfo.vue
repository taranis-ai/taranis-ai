<template>
  <v-tooltip class="mr-5">
    <template #activator="{ props }">
      <img
        v-if="icon"
        v-bind="props"
        :src="'data:image/png;base64,' + icon"
        :alt="source?.name"
        :height="height"
      />
      <v-icon v-else v-bind="props" :icon="typeIcon" />
    </template>
    <span>{{ source?.name }}</span>
  </v-tooltip>
</template>

<script>
import { getSourceInfo } from '@/utils/helpers.js'
import { computed } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'

export default {
  name: 'SourceInfo',
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const filterStore = useFilterStore()

    const source = computed(() => {
      return props.newsItem
        ? getSourceInfo(props.newsItem.osint_source_id)
        : null
    })

    const icon = computed(() => {
      return source.value?.icon
    })

    const height = computed(() => {
      return filterStore.compactView ? 24 : 32
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
      height,
      typeIcon
    }
  }
}
</script>
