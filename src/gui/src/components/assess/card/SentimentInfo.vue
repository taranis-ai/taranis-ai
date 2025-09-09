<template>
  <tr v-if="sentimentCategory">
    <td v-if="!compactView" class="py-0 news-item-title">
      <strong>{{ $t('assess.sentiment') }}:</strong>
    </td>
    <td class="py-0">
      {{ sentimentCategory }}
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
    sentimentCategory: {
      type: String,
      required: false,
      default: null
    },
    sentimentScore: {
      type: Number,
      required: false,
      default: undefined
    },
    compactView: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const sentimentTooltip = computed(() => {
      if (isNaN(props.sentimentScore)) {
        return `Sentiment is ${props.sentimentCategory} with no score available`
      }
      return `Sentiment is ${props.sentimentCategory} with a score of ${(props.sentimentScore * 100).toFixed(2)}%`
    })

    const sentimentEmoji = computed(() => {
      switch (props.sentimentCategory.toLowerCase()) {
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
      sentimentTooltip,
      sentimentEmoji
    }
  }
}
</script>
