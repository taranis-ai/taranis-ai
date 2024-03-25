<template>
  <v-container fluid>
    <div v-if="status === 'SUCCESS'">
      <v-card
        class="my-5"
        color="success"
        :title="`Source ${preview[0].source} could be gathered successfully`"
        :subtitle="`There are ${preview.length} entries`"
      />

      <v-card
        v-for="entry in preview"
        :key="entry.id"
        class="my-3 ml-5"
        :title="entry.title"
        :subtitle="entry.link"
        :text="entry.content"
      />
    </div>
    <div v-else-if="status === 'ERROR'">
      <v-card
        class="my-5"
        color="error"
        title="Error"
        subtitle="An error occurred while gathering the source"
        :text="preview.error"
      />
    </div>
    <div v-else-if="status === 'FAILURE'">
      <v-card
        class="my-5"
        color="error"
        title="Error"
        subtitle="An error occurred while gathering the source"
        :text="preview.exc_message"
      />
    </div>
    <div v-else>
      <v-card
        class="my-5"
        color="info"
        title="Loading"
        subtitle="Please wait while the source is being gathered"
      />
    </div>
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
    const status = ref('')

    getOSINTSSourcePreview(osint_source_id.value).then((response) => {
      status.value = response.data.status
      preview.value = response.data.result
    })

    return {
      preview,
      status
    }
  }
}
</script>
