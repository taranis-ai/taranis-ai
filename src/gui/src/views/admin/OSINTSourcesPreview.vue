<template>
  <v-container fluid>
    {{ preview }}
  </v-container>
</template>

<script>
import { getOSINTSSourcePreview } from '@/api/config'
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

export default {
  name: 'OSINTSourcesPreview',
  setup() {
    const route = useRoute()
    const osint_source_id = computed(() => route.params.source_id)
    const preview = ref(null)

    getOSINTSSourcePreview(osint_source_id.value).then((response) => {
      console.log(response)
      preview.value = response.data
    })

    return {
      preview
    }
  }
}
</script>
