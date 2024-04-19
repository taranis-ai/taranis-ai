<template>
  <tr>
    <td v-if="!compactView" style="max-width: 110px" class="py-0">
      <strong>{{ $t('assess.article') }}:</strong>
    </td>
    <td class="py-0" @click.stop>
      <v-tooltip>
        <template #activator="{ props }">
          <a
            class="text-primary"
            v-bind="props"
            :href="article?.link"
            target="_blank"
          >
            {{ article?.name }}
            <v-icon
              class="ml-2"
              size="x-small"
              color="primary"
              icon="mdi-open-in-new"
            />
          </a>
          <source-info :news-item="newsItem" />
        </template>
        <span>{{ article?.link }}</span>
      </v-tooltip>
    </td>
  </tr>
</template>

<script>
import { getCleanHostname } from '@/utils/helpers.js'
import SourceInfo from '@/components/assess/card/SourceInfo.vue'
import { computed } from 'vue'

export default {
  name: 'ArticleInfo',
  components: {
    SourceInfo
  },
  props: {
    newsItem: {
      type: Object,
      required: true
    },
    compactView: {
      type: Boolean,
      default: false
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

    return {
      article
    }
  }
}
</script>
