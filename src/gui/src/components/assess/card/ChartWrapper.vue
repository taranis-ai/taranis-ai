<template>
  <div v-if="shouldRender" :style="`height: ${chartHeight}px`">
    <week-chart :story="story" :timespan="timespan" />
  </div>
</template>

<script>
import WeekChart from './WeekChart.vue'
import { useFilterStore } from '@/stores/FilterStore'
import { computed } from 'vue'

export default {
  name: 'ChartWrapper',
  components: {
    WeekChart
  },
  props: {
    story: {
      type: Object,
      required: true
    },
    timespan: {
      type: Number,
      required: false,
      default: 7
    },
    chartHeight: {
      type: Number,
      required: false,
      default: 100
    }
  },
  setup(props) {
    const filterStore = useFilterStore()

    const shouldRender = computed(() => {
      return props.story && filterStore.showWeekChart
    })

    return {
      shouldRender
    }
  }
}
</script>
