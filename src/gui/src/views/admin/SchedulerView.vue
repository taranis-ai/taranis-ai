<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Scheduler</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <iframe :src="iframeSrc" width="100%" height="800px"></iframe>
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: 'SchedulerView',
  setup() {
    const iframeSrc = `${import.meta.env.BASE_URL}scheduler`
    return { iframeSrc }
  }
}
</script>
