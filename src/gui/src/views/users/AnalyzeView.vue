<template>
  <DataTable
    :sort-by="sortBy"
    :items="report_items_data"
    :show-top="true"
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
    <template #actionColumn="{ item }">
      <v-tooltip left>
        <template #activator="{ props }">
          <v-icon
            v-bind="props"
            color="secondary"
            @click.stop="cloneReport(item.id)"
          >
            mdi-file
          </v-icon>
        </template>
        <span>Clone Report</span>
      </v-tooltip>
    </template>
  </DataTable>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import { deleteReportItem } from '@/api/analyze'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { useFilterStore } from '@/stores/FilterStore'
import { useMainStore } from '@/stores/MainStore'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { onMounted, ref, computed } from 'vue'

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

    const updateData = () => {
      analyzeStore.loadReportItems().then(() => {
        mainStore.itemCountTotal = report_items.value.total_count
        mainStore.itemCountFiltered = report_items.value.items.length
      })
      analyzeStore.loadReportTypes()
    }

    const addItem = () => {
      router.push('/report/')
    }

    const editItem = (item) => {
      router.push('/report/' + item.id)
    }

    const deleteItem = (item) => {
      deleteReportItem(item)
        .then((response) => {
          notifySuccess(response)
          updateData()
        })
        .catch((error) => {
          notifyFailure(error)
        })
    }

    const cloneReport = (item_id) => {
      analyzeStore.cloneReport(item_id)
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection.map((item) => item.id)
    }

    onMounted(() => {
      updateData()
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
      deleteItem,
      cloneReport,
      selectionChange
    }
  }
}
</script>
