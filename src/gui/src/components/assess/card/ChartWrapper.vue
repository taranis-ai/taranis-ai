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
    const newest_published_date = new Date(
      Math.max(
        ...props.story.news_items.map((item) => new Date(item.published))
      )
    )
    const timespanDate = new Date()
    timespanDate.setDate(timespanDate.getDate() - props.timespan)

    const shouldRender = computed(() => {
      if (
        props.story &&
        filterStore.showWeekChart &&
        newest_published_date >= timespanDate
      ) {
        return true
      }
      return false
    })

    return {
      shouldRender
    }
  }
}
</script>
