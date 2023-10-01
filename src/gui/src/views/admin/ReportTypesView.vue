<template>
  <v-container fluid>
    <data-table
      v-model:items="report_item_types.items"
      :add-button="true"
      :header-filter="['id', 'title', 'description', 'actions']"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <report-type-form
      v-if="showForm"
      :report-type-data="formData"
      :attributes="attributes.items"
      :edit="edit"
      @updated="formUpdated"
    />
  </v-container>
</template>

<script>
import { defineComponent, ref, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import ReportTypeForm from '@/components/config/ReportTypeForm.vue'
import { deleteReportItemType } from '@/api/config'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { storeToRefs } from 'pinia'

import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'

export default defineComponent({
  name: 'ReportTypes',
  components: {
    DataTable,
    ReportTypeForm
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()
    const selected = ref([])
    const formData = ref({})
    const edit = ref(false)
    const showForm = ref(false)

    const { report_item_types, attributes } = storeToRefs(configStore)

    const updateData = () => {
      configStore.loadReportTypes().then(() => {
        mainStore.itemCountTotal = report_item_types.value.total_count
        mainStore.itemCountFiltered = report_item_types.value.items.length
      })
      configStore.loadAttributes()
    }

    const formUpdated = () => {
      console.debug('formUpdated')
      showForm.value = false
      updateData()
    }

    const addItem = () => {
      formData.value = {
        title: '',
        description: '',
        attribute_groups: []
      }
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      edit.value = true
      console.debug('editItem', item)
      formData.value = item
      showForm.value = true
    }

    const deleteItem = (item) => {
      if (!item.default) {
        deleteReportItemType(item)
          .then(() => {
            notifySuccess(`Successfully deleted ${item.title}`)
            updateData()
          })
          .catch(() => {
            notifyFailure(`Failed to delete ${item.title}`)
          })
      }
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    onMounted(() => {
      updateData()
    })

    return {
      selected,
      formData,
      showForm,
      edit,
      report_item_types,
      attributes,
      addItem,
      editItem,
      deleteItem,
      selectionChange,
      updateData,
      formUpdated
    }
  }
})
</script>
