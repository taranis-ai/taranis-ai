<template>
  <LineChart
    :chart-options="chartOptions"
    :chart-data="chart_data"
    :width="400"
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
      required: true
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
    last_seven_days() {
      return Array.from(Array(7).keys(), (i) => {
        const date = new Date()
        date.setDate(date.getDate() - i)
        return date.toLocaleDateString(undefined, {
          day: '2-digit',
          month: '2-digit'
        })
      }).reverse()
    },

    news_items_per_day() {
      const days = this.last_seven_days
      const items_per_day = this.story.news_items.reduce((acc, item) => {
        const day = new Date(item.news_item_data.published).toLocaleDateString(
          undefined,
          { day: '2-digit', month: '2-digit' }
        )
        if (day in acc) {
          acc[day] += 1
        } else {
          acc[day] = 1
        }
        return acc
      }, {})

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
        labels: this.last_seven_days,
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
  mounted() {}
}
</script>
