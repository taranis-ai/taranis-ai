<template>
  <tr v-if="sentiment_category">
    <td v-if="!compactView" style="max-width: 90px" class="py-0">
      <strong>{{ $t('assess.sentiment') }}:</strong>
    </td>
    <td class="py-0">
      {{ sentiment_category }}
      <v-tooltip activator="parent" location="left">
        <v-icon
          :color="
            sentiment_category === 'positive'
              ? 'success'
              : sentiment_category === 'negative'
                ? 'error'
                : 'grey'
          "
          size="x-small"
          icon="mdi-emoticon-outline"
        />
        {{ sentiment_score }}
      </v-tooltip>
    </td>
  </tr>
</template>

<script>
import { computed } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'SentimentInfo',
  props: {
    newsItem: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const sentiment_category = computed(() => {
      return props.newsItem?.attributes?.sentiment_category
    })

    const sentiment_score = computed(() => {
      return props.newsItem?.attributes?.sentiment_score
    })

    const filterStore = useFilterStore()
    const { compactView } = storeToRefs(filterStore)

    return {
      sentiment_category,
      sentiment_score,
      compactView
    }
  }
}
</script>
