<template>
  <v-container fluid>
    <iframe src="/api/doc" title="OpenAPI" class="openapi"></iframe>
  </v-container>
</template>

<script>
export default {
  name: 'OpenAPI',
  components: {},
  data: () => ({
    ui: null
  }),
  methods: {},
  mounted() {}
}
</script>
