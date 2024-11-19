<template>
  <tr>
    <td v-if="!compactView" class="py-0 news-item-title">
      <strong>{{ $t('assess.article') }}:</strong>
    </td>
    <td class="py-0">
      <v-tooltip>
        <template #activator="{ props }">
          <a v-bind="props" :href="article?.link" target="_blank" @click.stop>
            {{ article?.name }}
            <v-icon size="x-small" color="primary" icon="mdi-open-in-new" />
          </a>
        </template>
        <span>{{ article?.link }}</span>
      </v-tooltip>
    </td>
    <td class="text-right">
      <source-info :news-item="newsItem" />
    </td>
  </tr>
</template>

<script>
import { getCleanHostname } from '@/utils/helpers.js'
import SourceInfo from '@/components/assess/card/SourceInfo.vue'
import { computed } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'ArticleInfo',
  components: {
    SourceInfo
  },
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const article = computed(() => {
      return props.newsItem
        ? {
            name: getCleanHostname(props.newsItem.link),
            link: props.newsItem.link,
            type: props.newsItem.osint_source_id
          }
        : null
    })

    const filterStore = useFilterStore()
    const { compactView } = storeToRefs(filterStore)

    return {
      article,
      compactView
    }
  }
}
</script>
