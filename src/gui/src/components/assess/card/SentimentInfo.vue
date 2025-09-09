<template>
  <tr v-if="!compactView && sentimentCategory">
    <!-- reduced view, show only emoji + tooltip -->
    <template v-if="reduced">
      <td class="py-0">
        <v-tooltip activator="parent" location="bottom">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="x-small" :icon="sentimentEmoji" />
          </template>
          <span>{{ reducedTooltip }}</span>
        </v-tooltip>
      </td>
    </template>

    <!-- full view -->
    <template v-else>
      <td class="py-0 news-item-title">
        <strong>{{ $t('assess.sentiment') }}:</strong>
      </td>
      <td class="py-0">
        {{ sentimentCategory }}
        <v-tooltip activator="parent" location="bottom">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="x-small" :icon="sentimentEmoji" />
          </template>
          <span>{{ fullTooltip }}</span>
        </v-tooltip>
      </td>
    </template>
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
    },
    reduced: { type: Boolean, default: false }
  },
  setup(props) {
    const fullTooltip = computed(() => {
      if (!props.sentimentCategory) return ''
      if (isNaN(props.sentimentScore)) {
        return `Sentiment is ${props.sentimentCategory} with no score available`
      }
      return `Sentiment is ${props.sentimentCategory} with a score of ${(props.sentimentScore * 100).toFixed(2)}%`
    })

    const reducedTooltip = computed(() => {
      if (!props.sentimentCategory) return ''
      return `Sentiment is ${props.sentimentCategory}`
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
      fullTooltip,
      reducedTooltip,
      sentimentEmoji
    }
  }
}
</script>
