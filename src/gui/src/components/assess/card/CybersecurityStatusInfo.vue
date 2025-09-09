<template>
  <tr v-if="!compactView && cybersecurityStatus">
    <!-- reduced view, show only emoji + tooltip -->
    <template v-if="reducedView">
      <td class="py-0">
        <v-tooltip activator="parent" location="bottom">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="x-small" :icon="statusIcon" />
          </template>
          <span>{{ reducedTooltip }}</span>
        </v-tooltip>
      </td>
    </template>

    <!-- full view -->
    <template v-else>
      <td class="py-0 news-item-title">
        <strong>Cyberesecurity</strong>
      </td>
      <td class="py-0">
        {{ cybersecurityStatus }}
        <v-tooltip activator="parent" location="bottom">
          <template #activator="{ props }">
            <v-icon v-bind="props" size="x-small" :icon="statusIcon" />
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
  name: 'CybersecurityStatusInfo',
  props: {
    cybersecurityStatus: {
      type: String,
      required: false,
      default: null
    },
    cybersecurityScore: {
      type: Number,
      required: false,
      default: undefined
    },
    compactView: { type: Boolean, default: false },
    reducedView: { type: Boolean, default: false }
  },
  setup(props) {
    // tooltip for full mode
    const fullTooltip = computed(() => {
      if (!props.cybersecurityStatus) return ''
      if (isNaN(props.cybersecurityScore)) {
        return `Cybersecurity: ${props.cybersecurityStatus}`
      }
      return `Cybersecurity: ${props.cybersecurityStatus}, Score: ${(props.cybersecurityScore * 100).toFixed(2)}%`
    })

    // tooltip for reduced mode
    const reducedTooltip = computed(() => {
      if (!props.cybersecurityStatus) return ''
      return `Cybersecurity: ${props.cybersecurityStatus}`
    })

    const statusIcon = computed(() => {
      switch (props.cybersecurityStatus?.toLowerCase()) {
        case 'yes':
          return 'mdi-shield-half-full'
        case 'no':
          return 'mdi-shield-off'
        case 'mixed':
          return 'mdi-shield-half-full'
        default:
          return 'mdi-shield-outline'
      }
    })

    return {
      fullTooltip,
      reducedTooltip,
      statusIcon
    }
  }
}
</script>
