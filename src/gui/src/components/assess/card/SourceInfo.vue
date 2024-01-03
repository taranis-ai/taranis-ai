<template>
  <v-row>
    <v-col style="max-width: 110px" class="py-0">
      <strong>{{ $t('assess.source') }}:</strong>
    </v-col>
    <v-col class="py-0" @click.stop>
      <a :href="source?.link" target="_blank">
        {{ source?.name }}
      </a>
    </v-col>
  </v-row>
</template>

<script>
import { getCleanHostname } from '@/utils/helpers.js'
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
      return props.newsItem.news_item_data
        ? {
            name: getCleanHostname(props.newsItem.news_item_data.source),
            link: props.newsItem.news_item_data.link,
            type: props.newsItem.news_item_data.osint_source_id
          }
        : null
    })

    return {
      source
    }
  }
}
</script>

<style scoped></style>
