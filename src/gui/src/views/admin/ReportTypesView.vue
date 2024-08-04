<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Report Types Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <data-table
          v-model:items="report_item_types.items"
          :add-button="true"
          :header-filter="['id', 'title', 'description', 'actions']"
          @delete-item="deleteItem"
          @edit-item="editItem"
          @add-item="addItem"
          @update-items="updateData"
          @selection-change="selectionChange"
        >
          <template #titlebar>
            <ImportExport @import="importData" @export="exportData" />
          </template>
        </data-table>
        <report-type-form
          v-if="showForm"
          :report-type-data="formData"
          :attributes="attributes.items"
          :edit="edit"
          @updated="formUpdated"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { defineComponent, ref, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import ReportTypeForm from '@/components/config/ReportTypeForm.vue'
import ImportExport from '@/components/config/ImportExport.vue'
import {
  deleteReportItemType,
  importReportTypes,
  exportReportTypes
} from '@/api/config'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { storeToRefs } from 'pinia'

import { useConfigStore } from '@/stores/ConfigStore'

export default defineComponent({
  name: 'ReportTypes',
  components: {
    DataTable,
    ReportTypeForm,
    ImportExport
  },
  setup() {
    const configStore = useConfigStore()
    const selected = ref([])
    const formData = ref({})
    const edit = ref(false)
    const showForm = ref(false)

    const { report_item_types, attributes } = storeToRefs(configStore)

    const updateData = () => {
      Promise.all([configStore.loadReportTypes(), configStore.loadAttributes()])
    }

    const formUpdated = () => {
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
      showForm.value = false
      edit.value = true
      formData.value = item
      showForm.value = true
    }

    const deleteItem = (item) => {
      if (!item.default) {
        deleteReportItemType(item)
          .then((response) => {
            notifySuccess(response)
            showForm.value = false
            updateData()
          })
          .catch((error) => {
            notifyFailure(error)
          })
      }
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
      console.debug(`Selected: ${selected.value}`)
    }

    const importData = (data) => {
      importReportTypes(data)
        .then(() => {
          notifySuccess('Successfully imported Report Types')
          updateData()
        })
        .catch((error) => {
          notifyFailure(error)
        })
    }

    const exportData = () => {
      console.debug(`Exporting ${selected.value.join('&ids=')}`)
      let queryString = ''
      if (selected.value.length > 0) {
        queryString = 'ids=' + selected.value.join('&ids=')
      }
      exportReportTypes(queryString).then(() => {
        notifySuccess('Successfully exported Report Types')
      })
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
      importData,
      exportData,
      selectionChange,
      updateData,
      formUpdated
    }
  }
})
</script>
