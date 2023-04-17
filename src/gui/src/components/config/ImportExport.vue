<template>
  <div>
    <v-btn color="blue-grey" dark class="ml-4" @click="importClick">
      <v-icon>mdi-import</v-icon>Import
    </v-btn>
    <v-btn color="blue-grey" dark class="ml-4" @click="exportFile">
      <v-icon>mdi-export</v-icon>Export
    </v-btn>
    <input
      @change="fileSelected"
      accept="application/json"
      type="file"
      hidden
      ref="fileInput"
    />
  </div>
</template>

<script>
export default {
  name: 'ImportExport',
  components: {},
  emits: ['import', 'export'],
  data: () => ({}),
  computed: {},
  methods: {
    importClick() {
      this.$refs.fileInput.click()
    },
    fileSelected(event) {
      const file = event.target.files[0]
      const formData = new FormData()
      formData.append('file', file)
      this.$emit('import', formData)
    },
    exportFile() {
      this.$emit('export')
    }
  }
}
</script>
