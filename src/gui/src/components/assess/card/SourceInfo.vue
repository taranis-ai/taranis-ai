<template>
  <v-row>
    <v-col style="max-width: 110px" class="py-0">
      <strong>{{ $t('assess.source') }}:</strong>
    </v-col>
    <v-col class="py-0" @click.stop>
      <v-tooltip>
        <template #activator="{ props }">
          <img v-if="icon" v-bind="props" 
          :src="'data:image/png;base64,' + icon" :alt="source?.name" height="32" width="32"/> 
          <v-icon v-else v-bind="props" :icon="typeIcon" 
          />
        </template>
        <span>{{ source?.name }}</span>
      </v-tooltip>
    </v-col>
  </v-row>
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
