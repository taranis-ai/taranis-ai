<template>
  <div class="relevance-indicator">
    <v-badge
      :color="relevanceIndicator.color"
      :icon="relevanceIndicator.icon"
      :content="relevance"
      inline
    ></v-badge>
    <v-tooltip
      activator="parent"
      :text="`Relevance Score: ${relevance}`"
      location="right"
    />
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'RelevanceIndicator',
  props: {
    relevance: {
      type: Number,
      required: true
    }
  },
  setup(props) {
    const relevanceIndicator = computed(() => {
      return getRelevanceIndicator(props.relevance)
    })

    function getRelevanceIcon() {
      const threshold = 15
      if (props.relevance > threshold) return 'mdi-arrow-up-thick'
      if (props.relevance > threshold / 2) return 'mdi-arrow-top-right-thick'
      if (props.relevance > 0) return 'mdi-arrow-right-thick'
      if (props.relevance == 0) return 'mdi-minus-thick'
      if (props.relevance < 0) return 'mdi-arrow-bottom-right-thick'
      if (props.relevance < -threshold / 2) return 'mdi-arrow-down-thick'
      return 'mdi-minus-thick'
    }

    function interpolateColor(color_a, color_b, factor) {
      const r = Math.round(color_a.r + factor * (color_b.r - color_a.r))
      const g = Math.round(color_a.g + factor * (color_b.g - color_a.g))
      const b = Math.round(color_a.b + factor * (color_b.b - color_a.b))
      return { r, g, b }
    }

    function getRelevanceIndicator(value) {
      const min = 0
      const max = 15
      const mid = (min + max) / 2

      const start_color = { r: 255, g: 145, b: 61 }
      const middle_color = { r: 255, g: 230, b: 61 }
      const end_color = { r: 39, g: 189, b: 83 }
      const grey_color = { r: 212, g: 212, b: 212 }

      let interpolatedColor = grey_color

      if (value > max) {
        interpolatedColor = end_color
      } else if (value > 0) {
        if (value <= mid) {
          interpolatedColor = interpolateColor(
            start_color,
            middle_color,
            (value - min) / (mid - min)
          )
        } else {
          interpolatedColor = interpolateColor(
            middle_color,
            end_color,
            (value - mid) / (max - mid)
          )
        }
      }
      const color = `#${((1 << 24) + (interpolatedColor['r'] << 16) + (interpolatedColor['g'] << 8) + interpolatedColor['b']).toString(16).slice(1).toUpperCase()}`

      return { color: color, icon: getRelevanceIcon() }
    }

    return {
      relevanceIndicator
    }
  }
}
</script>

<style scoped>
.relevance-indicator {
  padding-top: 6px !important;
}
</style>
