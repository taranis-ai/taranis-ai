<template>
  <v-container fluid class="d-flex" style="height: 95vh">
    <v-row no-gutters class="flex-grow-1">
      <iframe
        :src="iframeSrc"
        width="100%"
        height="100%"
        class="no-style"
        style="border: none"
      />
    </v-row>
  </v-container>
</template>

<script>
export default {
  name: 'AdminDashboard',
  setup() {
    const iframeSrc = `${import.meta.env.BASE_URL}frontend`

    return { iframeSrc }
  }
}
</script>

<style scoped>
.no-style * {
  all: unset;
  display: revert;
  box-sizing: border-box;
}
</style>
