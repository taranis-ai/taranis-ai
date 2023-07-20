<template>
  <div>
    <v-btn
      color="green-darken-3"
      dark
      class="ml-4"
      prepend-icon="mdi-import"
      @click="importClick"
    >
      Import
    </v-btn>
    <v-btn
      color="teal-darken-4"
      dark
      class="ml-4"
      prepend-icon="mdi-export"
      @click="exportFile"
    >
      Export
    </v-btn>
    <input
      ref="fileInput"
      accept="application/json"
      type="file"
      hidden
      @change="fileSelected"
    />
  </div>
</template>

<script>
export default {
  name: 'ImportExport',
  emits: ['import', 'export'],
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
