<template>
  <v-container fluid class="d-flex" style="height: 95vh">
    <v-row no-gutters class="flex-grow-1">
      <iframe
        :src="iframeSrc"
        width="100%"
        height="100%"
        style="border: none"
      ></iframe>
    </v-row>
  </v-container>
</template>

<script>
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'SchedulerView',
  setup() {
    const iframeSrc = `${import.meta.env.BASE_URL}frontend/schedule`
    useMainStore().resetItemCount()

    return { iframeSrc }
  }
}
</script>
