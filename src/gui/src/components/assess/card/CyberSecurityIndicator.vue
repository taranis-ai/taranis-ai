<template>
  <div v-if="show_cybersecurity" class="cybersecurity-indicator">
    <v-badge
      :color="cybersecurity_icon_color.color"
      :icon="cybersecurity_icon_color.icon"
      inline
    ></v-badge>
    <v-tooltip activator="parent" :text="tooltipMessage" location="right" />
  </div>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'CyberSecurityIndicator',
  props: {
    newsItemArray: {
      type: Array,
      required: true
    },
    story: {
      type: Object,
      required: false
    }
  },
  setup(props) {
    const cybersecurity_scores = computed(() => {
      return props.newsItemArray.map((newsItem) => {
        const score = newsItem?.attributes?.find(
          (attr) => attr.key === 'cybersecurity'
        )?.value
        return score !== undefined ? parseFloat(score) : NaN
      })
    })

    const is_cybersecurity = computed(() => {
      if (props.story) {
        if (props.story.is_cybersecurity === true) return true
        else if (props.story.is_cybersecurity === false) return false
      }

      if (cybersecurity_scores.value.every((score) => isNaN(score))) return null

      const valid_scores = cybersecurity_scores.value.filter(
        (score) => !isNaN(score)
      )
      const mean_score =
        valid_scores.reduce((sum, value) => sum + value, 0) /
        valid_scores.length

      if (mean_score > 0.5) return true
      else return false
    })

    const show_cybersecurity = computed(() => {
      if (is_cybersecurity.value === null) return false
      else return true
    })

    const cybersecurity_icon_color = computed(() => {
      if (is_cybersecurity.value === true)
        return { color: '#4682B4', icon: 'mdi-shield' }
      else return { color: '#d4d4d4', icon: 'mdi-shield-off' }
    })

    const tooltipMessage = computed(() => {
      if (is_cybersecurity.value === true) return 'Cybersecurity-related'
      else return 'Not cybersecurity-related'
    })

    return {
      cybersecurity_scores,
      is_cybersecurity,
      show_cybersecurity,
      cybersecurity_icon_color,
      tooltipMessage
    }
  }
}
</script>

<style scoped>
.cybersecurity-indicator {
  padding-top: 6px !important;
}
</style>
