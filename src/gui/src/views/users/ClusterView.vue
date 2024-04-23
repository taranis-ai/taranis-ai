<template>
  <v-container v-if="cluster" fluid>
    <tag-table :tag-type="cluster" />
  </v-container>
</template>

<script>
import TagTable from '@/components/common/TagTable.vue'

export default {
  name: 'ClusterView',
  components: {
    TagTable
  },
  props: {
    cluster: {
      type: String,
      required: true
    }
  },
  setup() {}
}
</script>
