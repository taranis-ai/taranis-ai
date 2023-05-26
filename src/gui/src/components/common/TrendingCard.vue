<template>
  <div>
    <v-icon left>{{ tagIcon(cluster.tag_type) }}</v-icon>
    {{ tagText(cluster.tag_type) }}
    <span class="ml-4"> SIZE: {{ cluster.size }}</span>
    <v-divider class="mt-2 mb-2" />
    <trending-chart :dataPoints="cluster.published" :timespan="10" />
  </div>
</template>

<script>
import TrendingChart from '@/components/common/card/TrendingChart.vue'
import { tagIconFromType, tagTextFromType } from '@/utils/helpers'

export default {
  name: 'TrendingCard',
  props: {
    cluster: { type: Object, required: true }
  },
  components: {
    TrendingChart
  },
  data: function () {
    return {}
  },
  methods: {
    tagIcon(tag_type) {
      return tagIconFromType(tag_type)
    },
    tagText(tag_type) {
      return tagTextFromType(tag_type)
    }
  },
  computed: {},
  mounted() {}
}
</script>
