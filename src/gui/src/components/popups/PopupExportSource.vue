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
          <p class="ml-5">{{ message }}</p>
        </v-col>
      </v-row>

      <v-row class="pb-4">
        <v-col cols="12" class="d-flex flex-column align-start">
          <v-checkbox
            v-model="exportGroups"
            label="Export with Groups"
            density="compact"
            :hide-details="true"
          />
          <v-checkbox
            v-model="exportWithSecrets"
            label="Export with Secrets"
            density="compact"
            :hide-details="true"
          >
            <v-tooltip
              activator="parent"
              text="Include potentially sensitive information like proxy settings"
            />
          </v-checkbox>

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
    const exportWithSecrets = ref(false)

    const message = computed(() => {
      if (props.selected.length > 0) {
        return `Exporting ${props.selected.length} selected sources.`
      }
      return props.totalCount > 0
        ? `Exporting all ${props.totalCount} sources.`
        : 'Exporting all sources.'
    })

    async function exportData() {
      let queryString = ''
      if (props.selected.length > 0) {
        queryString = 'ids=' + props.selected.join('&ids=')
      }
      if (exportGroups.value) {
        queryString += '&groups=true'
      }
      if (exportWithSecrets.value) {
        queryString += '&secrets=true'
      }
      await exportOSINTSources(queryString)
      emit('close')
    }

    return {
      message,
      exportGroups,
      exportWithSecrets,
      exportData
    }
  }
}
</script>
