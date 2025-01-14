<template>
  <tr v-if="sentiment_category">
    <td v-if="!compactView" class="py-0 news-item-title">
      <strong>{{ $t('assess.sentiment') }}:</strong>
    </td>
    <td class="py-0">
      {{ sentiment_category }}
      <v-tooltip activator="parent" location="bottom">
        <template v-slot:activator="{ props }">
          <v-icon v-bind="props" size="x-small" :icon="sentimentEmoji" />
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

    const sentimentTooltip = computed(() => {
      if (isNaN(sentiment_score.value)) {
        return `Sentiment is ${sentiment_category.value} with no score available`
      }
      return `Sentiment is ${sentiment_category.value} with a score of ${(sentiment_score.value * 100).toFixed(2)}%`
    })

    const sentimentEmoji = computed(() => {
      switch (sentiment_category.value?.toLowerCase()) {
        case 'positive':
          return 'mdi-emoticon-happy-outline'
        case 'negative':
          return 'mdi-emoticon-sad-outline'
        case 'neutral':
          return 'mdi-emoticon-neutral-outline'
        default:
          return 'mdi-emoticon-outline'
      }
    })

    return {
      sentiment_category,
      sentiment_score,
      sentimentTooltip,
      sentimentEmoji
    }
  }
}
</script>
