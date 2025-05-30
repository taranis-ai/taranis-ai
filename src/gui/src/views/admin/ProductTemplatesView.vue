<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Product Templates Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          v-model:items="templates.items"
          :add-button="true"
          :header-filter="['path', 'actions']"
          @delete-item="deleteItem"
          @edit-item="editItem"
          @add-item="addItem"
          @update-items="updateData"
          @selection-change="selectionChange"
        >
          <template #titlebar>
            <v-btn
              v-if="selected.length === 1"
              color="blue-grey"
              dark
              class="ml-4"
              prepend-icon="mdi-content-copy"
              @click="copyTemplate"
            >
              Copy Template
            </v-btn>
          </template>

          <template #actionColumn="data">
            <v-tooltip left>
              <template #activator="{ props }">
                <v-icon
                  v-bind="props"
                  color="blue-grey"
                  icon="mdi-content-copy"
                  @click.stop="copyTemplate(data.item)"
                />
              </template>
              <span>Copy Template</span>
            </v-tooltip>
          </template>
        </DataTable>
        <TemplateForm
          v-if="showForm"
          :template-data="templateData"
          :template-name="templateName"
          :edit="edit"
          @updated="handleSubmit"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { deleteTemplate, updateTemplate, getTemplate } from '@/api/config'
import {
  notifySuccess,
  notifyFailure,
  getMessageFromError
} from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import DataTable from '@/components/common/DataTable.vue'
import TemplateForm from '@/components/config/TemplateForm.vue'

export default {
  name: 'ProductTemplatesView',
  components: {
    DataTable,
    TemplateForm
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()
    const edit = ref(false)
    const showForm = ref(false)
    const selected = ref([])

    const templateData = ref('')
    const templateName = ref('')

    const { templates } = storeToRefs(configStore)

    function updateData() {
      configStore.loadTemplates().then(() => {
        mainStore.itemCountTotal = templates.value.total_count
        mainStore.itemCountFiltered = templates.value.length
      })
    }

    function addItem() {
      templateData.value = ''
      edit.value = false
      showForm.value = true
    }

    function editItem(item) {
      templateName.value = item.path
      getTemplate(item.path).then((response) => {
        templateData.value =
          response.data !== '' ? atob(response.data.content) : ''
        edit.value = true
        showForm.value = true
      })
    }

    function handleSubmit(submittedData) {
      const data = {
        path: submittedData.templateName,
        data: btoa(submittedData.templateData)
      }
      updateItem(data)
      showForm.value = false
    }

    function deleteItem(item) {
      deleteTemplate(item.path)
        .then((response) => {
          notifySuccess(response.data.message)
          updateData()
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    }

    function updateItem(item) {
      updateTemplate(item)
        .then((response) => {
          notifySuccess(response.data.message)
          updateData()
        })
        .catch((error) => {
          notifyFailure(getMessageFromError(error))
        })
    }

    function selectionChange(items) {
      selected.value = items
    }

    function copyTemplate(item) {
      editItem(item)
      templateName.value = item.path + '_copy'
    }

    onMounted(() => {
      updateData()
    })

    return {
      edit,
      templates,
      showForm,
      selected,
      templateData,
      templateName,
      addItem,
      editItem,
      handleSubmit,
      copyTemplate,
      selectionChange,
      deleteItem,
      updateData
    }
  }
}
</script>
