<template>
  <v-card>
    <v-card-title> Share Items </v-card-title>
    <v-card-text>
      Select a report to share the item with:
      {{ reportItemSelection }}
      <v-select
        v-model="reportItemSelection"
        single-line
        label="Select Report"
        no-data-text="No reports found"
        :items="reportItems"
      />
    </v-card-text>
    <v-card-actions class="mt-1">
      <v-btn
        variant="outlined"
        class="text-lowercase text-red-darken-3 ml-3"
        prepend-icon="mdi-close"
        @click="close()"
      >
        abort
      </v-btn>
      <v-spacer></v-spacer>
      <v-btn
        variant="outlined"
        class="text-lowercase text-primary mr-3"
        prepend-icon="mdi-share-outline"
        @click="share()"
      >
        share
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { addAggregatesToReportItem } from '@/api/analyze'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { ref, onMounted, computed } from 'vue'

export default {
  name: 'PopupShareItems',
  props: {
    itemIds: {
      type: Array,
      default: () => []
    },
    dialog: Boolean
  },
  emits: ['close'],
  setup(props, { emit }) {
    const reportItemSelection = ref(null)
    const store = useAnalyzeStore()

    const { loadReportItems } = store

    const reportItems = computed(() =>
      store.report_items.items.map((item) => {
        return {
          title: item.title,
          value: item.id
        }
      })
    )

    const share = () => {
      addAggregatesToReportItem(reportItemSelection.value, props.itemIds)
      emit('close')
    }

    const close = () => {
      emit('close')
    }

    onMounted(() => {
      console.debug('PopupShareItems mounted')
      console.debug(props.itemIds)
      loadReportItems()
    })

    return {
      reportItems,
      reportItemSelection,
      share,
      close
    }
  }
}
</script>
