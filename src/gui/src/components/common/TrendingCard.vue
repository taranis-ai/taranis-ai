<template>
  <div>
    {{ cluster.name }}
    <v-divider></v-divider>
    SIZE: {{ cluster.size }}<br/>
    <week-chart :dataPoints="cluster.published" :timespan="10"/>
  </div>
</template>

<script>
import WeekChart from '@/components/assess/card/WeekChart'

export default {
  name: 'TrendingCard',
  props: {
    cluster: { type: Object, required: true }
  },
  components: {
    WeekChart
  },
  data: function () {
    return {

    }
  },
  computed: { },
  mounted() {}
}
</script>
