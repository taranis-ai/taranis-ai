<template>
  <!-- reduced view => inline span (no table cell) -->
  <span v-if="reducedView && cybersecurityStatus" class="inline-icon">
    <v-tooltip activator="parent" location="bottom">
      <template #activator="{ props }">
        <v-icon v-bind="props" size="x-small" class="mr-1" :icon="statusIcon" />
      </template>
      <span>{{ `Cybersecurity: ${cybersecurityStatus}` }}</span>
    </v-tooltip>
  </span>

  <!-- full view -->
  <tr v-else-if="!reducedView && cybersecurityStatus">
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
    reducedView: { type: Boolean, default: false }
  },
  setup(props) {
    const fullTooltip = computed(() => {
      if (!props.cybersecurityStatus) return ''
      if (isNaN(props.cybersecurityScore)) {
        return `Cybersecurity: ${props.cybersecurityStatus}`
      }
      return `Cybersecurity: ${props.cybersecurityStatus}, Score: ${props.cybersecurityScore.toFixed(4)}`
    })

    const statusIcon = computed(() => {
      switch (props.cybersecurityStatus?.toLowerCase()) {
        case 'yes':
          return 'mdi-shield-half-full'
        case 'no':
          return 'mdi-shield-off'
        case 'mixed':
          return 'mdi-shield-half'
        default:
          return 'mdi-shield-outline'
      }
    })

    return { fullTooltip, statusIcon }
  }
}
</script>

<style scoped>
.inline-icon {
  display: inline-flex;
  align-items: center;
}
</style>
