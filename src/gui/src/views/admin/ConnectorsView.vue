<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Connectors settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          :items="connectors"
          :header-filter="[
            'icon',
            'state',
            'name',
            'parameters.URL',
            'actions'
          ]"
          :add-button="true"
          @edit-item="editItem"
          @delete-item="deleteItem"
          @add-item="addItem"
          @update-items="updateData"
          @selection-change="selectionChange"
        >
          <template #titlebar>
            <!-- <ImportExport
              @import="importData"
              @export="showExportPopup = true"
            /> -->
          </template>
          <template #actionColumn="{ item }">
            <!-- No actions for connectors -->
          </template>
          <template #nodata>
            <v-empty-state
              icon="mdi-magnify"
              title="No Connectors Found"
              class="my-5"
            >
              <v-btn
                text="refresh"
                prepend-icon="mdi-refresh"
                @click.stop="updateData"
              />
            </v-empty-state>
          </template>
        </DataTable>
        <EditConfig
          v-if="showForm"
          :config-data="formData"
          :form-format="formFormat"
          :parameters="parameters"
          :title="editTitle"
          @submit="handleSubmit"
        />
        <v-dialog v-model="showDeletePopup" width="auto">
          <popup-delete-item
            @delete-item="forceDeleteItem(itemToDelete)"
            @close="showDeletePopup = false"
          />
        </v-dialog>
        <v-dialog v-model="showExportPopup" width="auto">
          <popup-export-source
            :selected="selected"
            :total-count="sourceTotalCount"
            @close="showExportPopup = false"
          />
        </v-dialog>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import ImportExport from '@/components/config/ImportExport.vue'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import PopupExportSource from '@/components/popups/PopupExportSource.vue'
import {
  deleteOSINTSource,
  updateConnector,
  // importOSINTSources,
  previewOSINTSSource,
  createConnector
} from '@/api/config'

import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'
import { storeToRefs } from 'pinia'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { ref, computed, onBeforeMount } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'OSINTSourcesView',
  components: {
    DataTable,
    EditConfig,
    ImportExport,
    PopupDeleteItem,
    PopupExportSource
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()
    const router = useRouter()

    const { connector_types, parameters } = storeToRefs(configStore)

    const connectors = computed(() => {
      return configStore.connectors.items
    })

    const connector_options = ref([])
    const selected = ref([])
    const formData = ref({})
    const edit = ref(false)
    const showForm = ref(false)
    const showDeletePopup = ref(false)
    const itemToDelete = ref({})
    const showExportPopup = ref(false)

    const formFormat = computed(() => {
      let base = [
        {
          name: 'id',
          label: 'ID',
          type: 'text',
          disabled: true
        },
        {
          name: 'last_collected',
          label: 'Last Collected',
          disabled: true,
          type: 'date'
        },
        {
          name: 'name',
          label: 'Name',
          type: 'text',
          rules: ['required']
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea'
        },
        {
          name: 'icon',
          label: 'Icon',
          type: 'file',
          icon: 'mdi-camera',
          rules: ['filesize'],
          placeholder: 'Pick an icon'
        },
        {
          name: 'type',
          label: 'Connector',
          type: 'select',
          items: connector_options.value,
          rules: ['required'],
          disabled: edit.value
        }
      ]
      if (formData.value.last_error_message) {
        base = [
          {
            name: 'last_error_message',
            label: 'Error Message',
            type: 'text',
            disabled: true,
            color: 'red'
          }
        ].concat(base)
      }
      return base
    })

    function updateData() {
      configStore.loadConnectors().then(() => {
        console.debug('connectors', configStore.connectors)
        mainStore.itemCountFiltered = configStore.connectors.items.length - 1
        mainStore.itemCountTotal = configStore.connectors.total_count - 1
      })
      configStore.loadWorkerTypes().then(() => {
        connector_options.value = connector_types.value
          .filter((connector) => connector.type !== 'manual_collector')
          .map((connector) => {
            return {
              value: connector.type,
              title: connector.name
            }
          })
      })
      configStore.loadParameters()
    }

    onBeforeMount(() => {
      updateData()
    })

    const addItem = () => {
      formData.value = objectFromFormat(formFormat.value)
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      formData.value = item
      edit.value = true
      showForm.value = true
    }

    const editTitle = computed(() => {
      return edit.value
        ? `Edit Source: '${formData.value['name']}'`
        : 'Add Source'
    })

    const handleSubmit = (submittedData) => {
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    async function forceDeleteItem(item) {
      showDeletePopup.value = false
      itemToDelete.value = {}
      try {
        const response = await deleteOSINTSource(item, true)
        notifySuccess(response.data)
        updateData()
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function deleteItem(item) {
      try {
        const response = await deleteOSINTSource(item)
        notifySuccess(response.data)
        updateData()
      } catch (error) {
        if (error.response.status === 409) {
          showDeletePopup.value = true
          itemToDelete.value = item
          return
        }
        notifyFailure(error)
      }
    }

    function createItem(item) {
      createConnector(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    async function updateItem(item) {
      try {
        const result = await updateConnector(item)
        notifySuccess(result.data.message)
        updateData()
      } catch (error) {
        notifyFailure(error)
      }
    }

    // async function importData(data) {
    //   try {
    //     await importOSINTSources(data)
    //     notifySuccess(`Successfully imported ${data.get('file').name}`)
    //     setTimeout(updateData, 1000)
    //   } catch (error) {
    //     notifyFailure('Failed to import sources')
    //   }
    // }

    function selectionChange(new_selection) {
      selected.value = new_selection
    }

    function previewSource(connector) {
      previewOSINTSSource(connector.id)
        .then(() => {
          router.push({
            name: 'osint_sources_preview',
            params: { source_id: connector.id }
          })
        })
        .catch(() => {
          notifyFailure(`Failed to preview ${connector.name}`)
        })
    }

    async function toggleState(connector) {
      await configStore.toggleOSINTSSourceState(connector)
    }

    return {
      parameters,
      connector_options,
      connectors,
      selected,
      formData,
      editTitle,
      showForm,
      showDeletePopup,
      showExportPopup,
      itemToDelete,
      formFormat,
      updateData,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      createItem,
      updateItem,
      // importData,
      previewSource,
      forceDeleteItem,
      toggleState,
      selectionChange
    }
  }
}
</script>
