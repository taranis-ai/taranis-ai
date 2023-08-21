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
      :accept="accepts"
      type="file"
      hidden
      @change="fileSelected"
    />
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'ImportExport',
  props: {
    accepts: {
      type: String,
      default: 'application/json'
    }
  },
  emits: ['import', 'export'],
  setup(props, { emit }) {
    const fileInput = ref(null)

    const importClick = () => {
      fileInput.value.click()
    }

    const fileSelected = (event) => {
      const file = event.target.files[0]
      const formData = new FormData()
      formData.append('file', file)
      emit('import', formData)
    }

    const exportFile = () => {
      emit('export')
    }

    return {
      fileInput,
      importClick,
      fileSelected,
      exportFile
    }
  }
}
</script>
