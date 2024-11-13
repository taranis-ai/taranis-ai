<template>
  <tr v-if="sentiment_category">
    <td v-if="!compactView" style="max-width: 90px" class="py-0">
      <strong>{{ $t('assess.sentiment') }}:</strong>
    </td>
    <td class="py-0">
      {{ formattedSentiment }}
      <v-tooltip activator="parent" location="bottom">
        <template v-slot:activator="{ props }">
          <v-icon
            v-bind="props"
            size="x-small"
            icon="mdi-emoticon-outline"
          />
        </template>
        <span>{{ sentimentTooltip }}</span>
      </v-tooltip>
    </td>
  </tr>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'SentimentInfo',
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
    const sentiment_category = computed(() => {
      return props.newsItem?.attributes?.find(
        (attr) => attr.key === 'sentiment_category'
      )?.value
    })

    const sentiment_score = computed(() => {
      const score = props.newsItem?.attributes?.find(
        (attr) => attr.key === 'sentiment_score'
      )?.value
      return score !== undefined ? parseFloat(score) : NaN
    })

    const formattedSentiment = computed(() => {
      if (isNaN(sentiment_score.value)) {
        return 'Sentiment: Not available'
      }

      const percentage = (sentiment_score.value * 100).toFixed(2)
      return `${sentiment_category.value}: ${percentage}%`
    })

    const sentimentTooltip = computed(() => {
      return `Sentiment is ${sentiment_category.value} with a score of ${(sentiment_score.value * 100).toFixed(2)}%`
    })

    return {
      sentiment_category,
      sentiment_score,
      formattedSentiment,
      sentimentTooltip
    }
  }
}
</script>
