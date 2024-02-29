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
            <v-icon class="ml-2" size="x-small" color="primary"
              >mdi-open-in-new</v-icon
            >
          </a>
        </template>
        <span>{{ article?.link }}</span>
      </v-tooltip>
    </td>
  </tr>
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
    },
    compactView: {
      type: Boolean,
      default: false
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
