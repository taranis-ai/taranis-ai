<template>
  <v-card>
    <v-card-title> Add to Report </v-card-title>
    <v-card-text>
      Select a report to add the item to:
      <v-autocomplete
        v-model="reportItemSelection"
        single-line
        label="Select Report"
        no-data-text="No reports found"
        :items="reportItems"
        menu-icon="mdi-chevron-down"
      />
      <v-spacer />
      <v-btn variant="outlined" block :to="reportItemProps">
        <v-tooltip
          activator="parent"
          text="Create a new report with these Stories"
        />
        Create new Report
      </v-btn>
    </v-card-text>
    <v-card-actions class="mt-1">
      <v-btn
        variant="outlined"
        class="text-lowercase text-red-darken-3 ml-3"
        prepend-icon="mdi-close"
        :text="$t('generic.abort')"
        @click="close()"
      />
      <v-spacer />
      <v-btn
        variant="outlined"
        class="text-lowercase text-primary mr-3"
        prepend-icon="mdi-share-outline"
        @click="share()"
      >
        Add to Report
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { ref, onMounted, computed } from 'vue'

export default {
  name: 'PopupShareToReport',
  props: {
    itemIds: {
      type: Array,
      default: () => []
    },
    dialog: Boolean
  },
  emits: ['close'],
  setup(props, { emit }) {
    const analyzeStore = useAnalyzeStore()
    const reportItemSelection = ref(analyzeStore.last_report)

    const reportItems = computed(() => analyzeStore.getReportItemsList)

    if (
      reportItemSelection.value &&
      !reportItems.value.find((r) => r.value === reportItemSelection.value)
    ) {
      analyzeStore.last_report = null
    }
    const reportItemProps = ref({
      name: 'report',
      query: { story: props.itemIds }
    })

    const share = () => {
      analyzeStore.addStoriesToReport(reportItemSelection.value, props.itemIds)
      emit('close')
    }

    const close = () => {
      emit('close')
    }

    onMounted(() => {
      analyzeStore.loadReportItems()
    })

    return {
      reportItems,
      reportItemSelection,
      reportItemProps,
      share,
      close
    }
  }
}
</script>
