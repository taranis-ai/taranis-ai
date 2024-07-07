<template>
  <DataTable
    :sort-by="sortBy"
    :items="report_items_data"
    :show-top="true"
    :search-bar="false"
    :header-filter="[
      'completed',
      'type',
      'title',
      'created',
      'stories',
      'actions'
    ]"
    :items-per-page="reportFilter.limit"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
    @update-items="updateData"
    @selection-change="selectionChange"
  >
    <template #titlebar>
      <h2>Reports</h2>
    </template>
    <template #actionColumn="{ item }">
      <v-tooltip left>
        <template #activator="{ props }">
          <v-icon
            v-bind="props"
            color="secondary"
            @click.stop="cloneReport(item.id)"
          >
            mdi-content-copy
          </v-icon>
        </template>
        <span>Clone Report</span>
      </v-tooltip>
    </template>
  </DataTable>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { useFilterStore } from '@/stores/FilterStore'
import { useMainStore } from '@/stores/MainStore'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { onMounted, ref, computed, onUnmounted } from 'vue'

export default {
  name: 'AnalyzeView',
  components: {
    DataTable
  },
  setup() {
    const sortBy = ref([{ key: 'created', order: 'desc' }])

    const mainStore = useMainStore()
    const analyzeStore = useAnalyzeStore()
    const filterStore = useFilterStore()
    const router = useRouter()
    const { reportFilter } = storeToRefs(filterStore)

    const { report_item_types, report_items } = storeToRefs(analyzeStore)
    const selected = ref([])

    const report_items_data = computed(
      () => analyzeStore.getReportItemsTableData
    )

    async function updateData() {
      await analyzeStore.loadReportTypes()
      await analyzeStore.updateReportItems()
    }

    const addItem = () => {
      router.push('/report/')
    }

    const editItem = (item) => {
      router.push('/report/' + item.id)
    }

    const cloneReport = (item_id) => {
      analyzeStore.cloneReport(item_id)
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection.map((item) => item.id)
    }

    onMounted(() => {
      analyzeStore.loadReportTypes()
    })

    onUnmounted(() => {
      mainStore.resetItemCount()
    })

    return {
      report_item_types,
      report_items_data,
      report_items,
      reportFilter,
      selected,
      sortBy,
      updateData,
      addItem,
      editItem,
      deleteItem: analyzeStore.removeReport,
      cloneReport,
      selectionChange
    }
  }
}
</script>
