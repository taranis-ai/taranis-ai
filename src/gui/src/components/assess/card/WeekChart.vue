<template>
  <Bar :options="chartOptions" :data="chart_data" update-mode="active" />
</template>

<script>
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  Filler,
  LineElement,
  BarElement,
  LinearScale,
  CategoryScale,
  PointElement,
  LineController
} from 'chart.js'
import { useAssessStore } from '@/stores/AssessStore'
import { computed } from 'vue'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  Filler,
  LineElement,
  BarElement,
  LinearScale,
  CategoryScale,
  PointElement,
  LineController
)

export default {
  name: 'WeekChart',
  components: {
    Bar
  },
  props: {
    story: {
      type: Object || null,
      required: false,
      default: null
    },
    timespan: {
      type: Number,
      required: false,
      default: 7
    }
  },
  setup(props) {
    const assessStore = useAssessStore()

    const last_n_days = computed(() =>
      Array.from(Array(props.timespan).keys(), (i) => {
        const date = new Date()
        date.setDate(date.getDate() - i)
        return date.toLocaleDateString(undefined, {
          day: '2-digit',
          month: '2-digit'
        })
      }).reverse()
    )

    const story_items = computed(() =>
      props.story.news_items.reduce((acc, item) => {
        const day = new Date(item.published).toLocaleDateString(undefined, {
          day: '2-digit',
          month: '2-digit'
        })
        acc[day] = (acc[day] || 0) + 1
        return acc
      }, {})
    )

    const news_items_per_day = computed(() => {
      const items_per_day = story_items.value
      return last_n_days.value.map((day) => items_per_day[day] || 0)
    })

    const chart_colors = computed(() =>
      news_items_per_day.value.map((item) => {
        if (item >= 20) {
          return 'rgba(255, 0, 0, 1.0)'
        } else {
          return 'rgba(233, 198, 69, 0.5)'
        }
      })
    )

    const chart_data = computed(() => ({
      labels: last_n_days.value,
      datasets: [
        {
          label: 'items/day',
          data: news_items_per_day.value,
          backgroundColor: chart_colors.value,
          type: 'bar',
          yAxisID: 'y1',
          order: 2
        },
        {
          label: 'items/day',
          type: 'line',
          data: news_items_per_day.value,
          borderColor: '#666',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y2',
          order: 1
        }
      ]
    }))

    return {
      chart_data,
      chartOptions: assessStore.weekChartOptions
    }
  }
}
</script>
