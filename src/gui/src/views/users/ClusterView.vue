<template>
  <v-container v-if="tag_type" fluid style="min-height: 100vh">
    <tag-table :tag-type="tag_type" />
  </v-container>
</template>

<script>
import { computed } from 'vue'
import TagTable from '@/components/common/TagTable.vue'
import { useRoute } from 'vue-router'

export default {
  name: 'ClusterView',
  components: {
    TagTable
  },
  setup() {
    const route = useRoute()

    const tag_type = computed(() => route.params.cluster)

    return {
      tag_type
    }
  }
}
</script>
