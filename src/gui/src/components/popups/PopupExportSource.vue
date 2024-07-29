<template>
  <v-card>
    <v-btn outlined color="primary" @click="$emit('close')">
      <v-icon>mdi-close</v-icon>
    </v-btn>

    <v-container>
      <v-row>
        <v-col cols="12">
          <h2 class="font-weight-regular dark-grey--text text-capitalize pt-0">
            Export OSINT Sources
          </h2>
        </v-col>
      </v-row>

      <v-row class="pb-4">
        <v-row class="mt-4 mb-0">
          <v-col cols="12" sm="12" class="d-flex flex-column align-start">
            <p class="ml-5">{{ message }}</p>

            <v-checkbox v-model="exportGroups" label="Export with Groups" />

            <v-btn
              outlined
              block
              color="primary"
              prepend-icon="mdi-file-export-outline"
              text="download export"
              @click="exportData()"
            />
          </v-col>
        </v-row>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
import { ref, computed } from 'vue'
import { exportOSINTSources } from '@/api/config'

export default {
  name: 'PopupExportSource',
  props: {
    totalCount: {
      type: Number,
      required: true
    },
    selected: {
      type: Array,
      default: () => []
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const exportGroups = ref(false)

    const message = computed(() => {
      if (props.selected.length > 0) {
        return `Exporting ${props.selected.length} selected sources.`
      }
      return `Exporting all ${props.totalCount} sources.`
    })

    async function exportData() {
      let queryString = ''
      if (props.selected.length > 0) {
        queryString = 'ids=' + props.selected.join('&ids=')
      }
      if (exportGroups.value) {
        queryString += '&groups=true'
      }
      await exportOSINTSources(queryString)
      emit('close')
    }

    return {
      message,
      exportGroups,
      exportData
    }
  }
}
</script>
