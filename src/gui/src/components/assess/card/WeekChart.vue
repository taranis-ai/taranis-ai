<template>
  <Bar
    v-if="shouldRender"
    :options="chartOptions"
    :data="chart_data"
    update-mode="active"
  />
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
import { mapState } from 'pinia'
import { useAssessStore } from '@/stores/AssessStore'
import { useFilterStore } from '@/stores/FilterStore'

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
      shouldRender: false
    }
  },
  computed: {
    ...mapState(useFilterStore, ['chartFilter']),
    ...mapState(useAssessStore, ['max_item']),
    chart_style() {
      return {
        height: this.chartHeight + 'px',
        width: this.chartWidth + 'px',
        position: 'relative'
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
    chartOptions() {
      if (this.chartFilter.y2max) {
        return {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y1: {
              position: 'left',
              beginAtZero: true,
              ticks: {
                stepSize: 1
              }
            },
            y2: {
              position: 'right',
              beginAtZero: true,
              max: parseInt(this.chartFilter.y2max),
              grid: {
                // display gridlines only for y1
                drawOnChartArea: false
              },
              ticks: {
                stepSize: 1
              }
            }
          },
          plugins: {
            filler: {
              propagate: false
            },
            legend: {
              display: false
            },
            tooltip: {
              mode: 'index',
              intersect: false
            }
          }
        }
      }
      return {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y1: {
            position: 'left',
            beginAtZero: true,
            ticks: {
              stepSize: 1
            }
          },
          y2: {
            position: 'right',
            beginAtZero: true,
            max: parseInt(this.max_item),
            grid: {
              // display gridlines only for y1
              drawOnChartArea: false
            },
            ticks: {
              stepSize: 1
            }
          }
        },
        plugins: {
          filler: {
            propagate: false
          },
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        }
      }
    },
    news_items_per_day() {
      let items_per_day = {}
      items_per_day = this.story_items

      const days = this.last_n_days

      return days.map((day) => {
        if (day in items_per_day) {
          return items_per_day[day]
        } else {
          return 0
        }
      })
    },
    chart_colors() {
      return this.news_items_per_day.map((item) => {
        if (item >= this.chartFilter.threshold) {
          return 'rgba(255, 0, 0, 1.0)'
        } else {
          return 'rgba(127, 116, 234, 1.0)'
        }
      })
    },
    chart_data() {
      return {
        labels: this.last_n_days,
        datasets: [
          {
            label: 'items/day',
            data: this.news_items_per_day,
            backgroundColor: this.chart_colors,
            type: 'bar',
            yAxisID: 'y1',
            order: 2
          },
          {
            label: 'items/day',
            type: 'line',
            data: this.news_items_per_day,
            borderColor: '#000',
            backgroundColor: '#000',
            yAxisID: 'y2',
            order: 1
          }
        ]
      }
    }
  },
  updated() {
    //console.log('card rendered!')
  },
  mounted() {
    if (this.story) {
      this.shouldRender = true
    } else {
      console.error('No data provided to WeekChart')
    }
  }
}
</script>
