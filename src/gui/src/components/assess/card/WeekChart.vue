<template>
  <LineChart
    :chart-options="chartOptions"
    :chart-data="chart_data"
    :height="200"
  />
</template>

<script>
import { Line as LineChart } from 'vue-chartjs/legacy'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  CategoryScale,
  PointElement
} from 'chart.js'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  LineElement,
  LinearScale,
  CategoryScale,
  PointElement
)

export default {
  name: 'WeekChart',
  components: {
    LineChart
  },
  props: {
    story: {
      type: Object,
      required: false,
      default: () => {}
    },
    timespan: {
      type: Number,
      required: false,
      default: 7
    },
    dataPoints: {
      type: Array,
      required: false,
      default: () => []
    }
  },
  data: function () {
    return {
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false
      }
    }
  },
  computed: {
    last_n_days() {
      return Array.from(Array(this.timespan).keys(), (i) => {
        const date = new Date()
        date.setDate(date.getDate() - i)
        return date.toLocaleDateString(undefined, {
          day: '2-digit',
          month: '2-digit'
        })
      }).reverse()
    },

    data_point_items() {
      const dateCounts = {}
      this.dataPoints.forEach(date => {
        const day = new Date(date).toLocaleDateString(undefined, {
          day: '2-digit',
          month: '2-digit'
        })
        dateCounts[day] = (dateCounts[day] || 0) + 1
      })
      return dateCounts
    },

    story_items() {
      return this.story.news_items.reduce((acc, item) => {
        const day = new Date(item.news_item_data.published).toLocaleDateString(
          undefined,
          { day: '2-digit', month: '2-digit' }
        )
        acc[day] = (acc[day] || 0) + 1
        return acc
      }, {})
    },

    news_items_per_day() {
      let items_per_day = {}
      if (this.dataPoints.length > 0) {
        items_per_day = this.data_point_items
      }
      if (this.story) {
        items_per_day = this.story_items
      }
      const days = this.last_n_days

      return days.map((day) => {
        if (day in items_per_day) {
          return items_per_day[day]
        } else {
          return 0
        }
      })
    },

    chart_data() {
      return {
        labels: this.last_n_days,
        datasets: [
          {
            label: 'Anzahl der Artikel',
            data: this.news_items_per_day
          }
        ]
      }
    }
  },
  updated() {
    // console.log('card rendered!')
  },
  mounted() {
    if (!this.story && !this.dataPoints) {
      console.error('No data provided to WeekChart')
    }
  }
}
</script>
