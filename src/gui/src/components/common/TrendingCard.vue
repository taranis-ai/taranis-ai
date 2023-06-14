<template>
  <v-card-subtitle>
    <span>
      <v-icon :icon="tagIcon(cluster.tag_type)" />
      {{ tagText(cluster.tag_type) }}
    </span>
    <span class="ml-5"> Cluster size: {{ cluster.size }}</span>
    <v-divider class="mt-2 mb-2" />
  </v-card-subtitle>
  <v-card-text>
    <trending-chart :data-points="cluster.published" :timespan="10" />
  </v-card-text>
</template>

<script>
import TrendingChart from '@/components/common/card/TrendingChart.vue'
import { tagIconFromType, tagTextFromType } from '@/utils/helpers'

export default {
  name: 'TrendingCard',
  components: {
    TrendingChart
  },
  props: {
    cluster: { type: Object, required: true }
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
  }
}
</script>
