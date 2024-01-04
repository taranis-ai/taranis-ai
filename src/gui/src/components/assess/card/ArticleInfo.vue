<template>
  <v-row>
    <v-col style="max-width: 110px" class="py-0">
      <strong>{{ $t('assess.article') }}:</strong>
    </v-col>
    <v-col class="py-0" @click.stop>
      <v-tooltip>
        <template #activator="{ props }">
          <a v-bind="props" :href="article?.link" target="_blank">
            {{ article?.name }}
          </a>
        </template>
        <span>{{ article?.link }}</span>
      </v-tooltip>
    </v-col>
  </v-row>
</template>

<script>
import { getCleanHostname } from '@/utils/helpers.js'
import { computed } from 'vue'

export default {
  name: 'ArticleInfo',
  props: {
    newsItemData: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const article = computed(() => {
      return props.newsItemData
        ? {
            name: getCleanHostname(props.newsItemData.source),
            link: props.newsItemData.link,
            type: props.newsItemData.osint_source_id
          }
        : null
    })

    return {
      article
    }
  }
}
</script>
