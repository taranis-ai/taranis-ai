<template>
  <LineChart
    :options="chartOptions"
    :data="chart_data"
    :style="chart_style"
    :height="chartHeight"
    update-mode="active"
  />
</template>

<script>
import { Line as LineChart } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  Filler,
  LineElement,
  LinearScale,
  CategoryScale,
  PointElement
} from 'chart.js'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  Filler,
  LineElement,
  LinearScale,
  CategoryScale,
  PointElement
)

export default {
  name: 'TrendingChart',
  components: {
    LineChart
  },
  props: {
    timespan: {
      type: Number,
      required: false,
      default: 7
    },
    dataPoints: {
      type: Array,
      required: false,
      default: () => []
    },
    chartHeight: {
      type: Number,
      required: false,
      default: 150
    },
    chartWidth: {
      type: Number,
      required: false,
      default: 400
    }
  },
  data: function () {
    return {
      chartOptions: {
        responsive: true,
        maintainAspectRatio: false,
        elements: {
          line: {
            tension: 0.4
          }
        },
        plugins: {
          filler: {
            propagate: false
          },
          legend: {
            display: false
          }
        }
      }
    }
  },
  computed: {
    chart_style() {
      return {
        height: this.chartHeight + 'px',
        width: this.chartWidth + 'px'
      }
    },

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
      this.dataPoints.forEach((date) => {
        const day = new Date(date).toLocaleDateString(undefined, {
          day: '2-digit',
          month: '2-digit'
        })
        dateCounts[day] = (dateCounts[day] || 0) + 1
      })
      return dateCounts
    },

    news_items_per_day() {
      let items_per_day = {}
      if (this.dataPoints.length > 0) {
        items_per_day = this.data_point_items
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
            data: this.news_items_per_day,
            showLine: false,
            backgroundColor: 'rgba(127, 116, 234, 1.0)',
            fill: true
          }
        ]
      }
    }
  },
  updated() {
    // console.log('card rendered!')
  },
  mounted() {
    if (!this.dataPoints) {
      console.error('No data provided to TrendingChart')
    }
  }
}
</script>
