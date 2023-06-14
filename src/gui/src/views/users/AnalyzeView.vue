<template>
  <DataTable
    :items="report_items_data"
    :add-button="false"
    :search-bar="false"
    :header-filter="['completed', 'type', 'title', 'created']"
    sort-by-item="id"
    :action-column="true"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
    @update-items="updateData"
    @selection-change="selectionChange"
  >
    <template #actionColumn>
      <v-tooltip left>
        <template #activator="{ props }">
          <v-icon
            v-bind="props"
            color="secondary"
            @click.stop="createProduct(item)"
          >
            mdi-file
          </v-icon>
        </template>
        <span>Create Product</span>
      </v-tooltip>
    </template>
  </DataTable>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import {
  deleteReportItem,
  createReportItem,
  updateReportItem
} from '@/api/analyze'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
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
    const mainStore = useMainStore()
    const analyzeStore = useAnalyzeStore()
    const router = useRouter()

    const { report_item_types, report_items } = storeToRefs(analyzeStore)
    const selected = ref([])

    const report_items_data = computed(() => {
      return report_items.value.items.map((item) => {
        return {
          id: item.id,
          completed: item.completed,
          title: item.title,
          created: item.created,
          type: report_item_types.value.items.find(
            (type) => type.id === item.report_item_type_id
          )?.title
        }
      })
    })

    const updateData = () => {
      analyzeStore.loadReportItems().then(() => {
        mainStore.itemCountTotal = report_items.value.total_count
        mainStore.itemCountFiltered = report_items.value.items.length
      })
      analyzeStore.loadReportTypes()
    }

    const addItem = () => {
      router.push('/report/0')
    }

    const editItem = (item) => {
      router.push('/report/' + item.id)
    }

    const deleteItem = (item) => {
      deleteReportItem(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.title}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.title}`)
        })
    }

    const createItem = (item) => {
      createReportItem(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.title}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.title}`)
        })
    }

    const updateItem = (item) => {
      updateReportItem(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.title}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.title}`)
        })
    }

    const createProduct = () => {
      router.push({ name: 'product', params: { id: 0 } })
    }

    const selectionChange = (selected) => {
      state.selected = selected.map((item) => item.id)
    }

    onMounted(() => {
      updateData()
    })

    return {
      report_item_types,
      report_items_data,
      report_items,
      selected,
      updateData,
      addItem,
      editItem,
      deleteItem,
      createItem,
      updateItem,
      createProduct,
      selectionChange
    }
  }
}
</script>
