<template>
  <v-tooltip>
    <template #activator="{ props }">
      <img
        v-if="icon"
        v-bind="props"
        class="ml-4"
        :src="'data:image/png;base64,' + icon"
        :alt="source?.name"
        height="32"
      />
      <v-icon v-else v-bind="props" :icon="typeIcon" />
    </template>
    <span>{{ source?.name }}</span>
  </v-tooltip>
</template>

<script>
import { getSourceInfo } from '@/utils/helpers.js'
import { computed } from 'vue'

export default {
  name: 'SourceInfo',
  props: {
    newsItemData: {
      type: Object,
      required: true
    },
    compactView: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const source = computed(() => {
      return props.newsItemData
        ? getSourceInfo(props.newsItemData.osint_source_id)
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
