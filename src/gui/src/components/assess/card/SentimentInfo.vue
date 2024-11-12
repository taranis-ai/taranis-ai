<template>
  <tr v-if="sentiment_category">
    <td v-if="!compactView" style="max-width: 90px" class="py-0">
      <strong>{{ $t('assess.sentiment') }}:</strong>
    </td>
    <td class="py-0">
      {{ formattedSentiment }}
      <v-tooltip activator="parent" location="bottom">
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
    }
  },
  setup(props) {
    const sentiment_category = computed(() => {
      return props.newsItem?.attributes?.find(
        (attr) => attr.key === 'sentiment_category'
      )?.value
    })

    const sentiment_score = computed(() => {
      return parseFloat(
        props.newsItem?.attributes?.find((attr) => attr.key === 'sentiment_score')?.value
      )
    })

    const formattedSentiment = computed(() => {
      if (!sentiment_score.value || isNaN(sentiment_score.value)) {
        return "Sentiment: Not available"
      }
      
      const percentage = (sentiment_score.value * 100).toFixed(2)
      return `${sentiment_category.value}: ${percentage}%`
    })

    return {
      sentiment_category,
      sentiment_score,
      formattedSentiment
    }
  }
}
</script>
