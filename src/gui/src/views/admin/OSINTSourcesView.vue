<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>OSINT Sources Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          :items="osint_sources"
          :header-filter="[
            'icon',
            'state',
            'name',
            'parameters.FEED_URL',
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
            <ImportExport
              @import="importData"
              @export="showExportPopup = true"
            />
            <v-btn
              dark
              color="blue-grey"
              class="ml-4"
              prepend-icon="mdi-run"
              @click="collectAllSources"
            >
              Collect Sources
            </v-btn>
          </template>
          <template #actionColumn="source">
            <v-tooltip left>
              <template #activator="{ props }">
                <v-icon
                  v-bind="props"
                  color="secondary"
                  icon="mdi-run"
                  @click.stop="collectSource(source.item)"
                />
              </template>
              <span>Collect Source</span>
            </v-tooltip>
            <v-tooltip left>
              <template #activator="{ props }">
                <v-icon
                  v-bind="props"
                  color="secondary"
                  icon="mdi-file-find"
                  @click.stop="previewSource(source.item)"
                />
              </template>
              <span>Preview Source</span>
            </v-tooltip>
            <v-tooltip left>
              <template #activator="{ props }">
                <v-icon
                  v-bind="props"
                  :color="source.item.state > '-2' ? 'green' : 'red'"
                  :icon="
                    source.item.state > '-2'
                      ? 'mdi-toggle-switch-outline'
                      : 'mdi-toggle-switch-off-outline'
                  "
                  @click.stop="toggleState(source.item)"
                />
              </template>
              <span>{{ source.item.state > '-2' ? 'Disable' : 'Enable' }}</span>
            </v-tooltip>
          </template>
          <template #nodata>
            <v-empty-state
              icon="mdi-magnify"
              title="No OSINTSources Found"
              class="my-5"
            >
              <v-btn
                text="refresh"
                prepend-icon="mdi-refresh"
                @click.stop="updateData"
              />
              <v-btn
                v-if="sourceTotalCount < 1"
                text="load default sources"
                prepend-icon="mdi-database"
                @click.stop="loadDefaultSources()"
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
  createOSINTSource,
  updateOSINTSource,
  importOSINTSources,
  collectOSINTSSource,
  previewOSINTSSource,
  collectAllOSINTSSources
} from '@/api/config'

import { getDefaultSoures } from '@/api/static'
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

    const { collector_types, parameters } = storeToRefs(configStore)

    const osint_sources = computed(() => {
      // remove the source where id === 'manual'
      return configStore.osint_sources.items.filter(
        (source) => source.id !== 'manual'
      )
    })

    const collector_options = ref([])
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
          label: 'Collector',
          type: 'select',
          items: collector_options.value,
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
      configStore.loadOSINTSources().then(() => {
        mainStore.itemCountFiltered = configStore.osint_sources.items.length - 1
        mainStore.itemCountTotal = configStore.osint_sources.total_count - 1
      })
      configStore.loadWorkerTypes().then(() => {
        collector_options.value = collector_types.value
          .filter((collector) => collector.type !== 'manual_collector')
          .map((collector) => {
            return {
              value: collector.type,
              title: collector.name
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
      createOSINTSource(item)
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
        const result = await updateOSINTSource(item)
        notifySuccess(result.data.message)
        updateData()
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function loadDefaultSources() {
      try {
        const response = await getDefaultSoures()
        const file = await response.data
        const formData = new FormData()
        formData.append('file', file, 'default_sources.json')
        await importData(formData)
      } catch (error) {
        notifyFailure('Failed to import default sources')
      }
    }

    async function importData(data) {
      try {
        await importOSINTSources(data)
        notifySuccess(`Successfully imported ${data.get('file').name}`)
        setTimeout(updateData, 1000)
      } catch (error) {
        notifyFailure('Failed to import sources')
      }
    }

    function selectionChange(new_selection) {
      selected.value = new_selection
    }

    function collectAllSources() {
      collectAllOSINTSSources()
        .then(() => {
          notifySuccess('Successfully collected all sources')
        })
        .catch(() => {
          notifyFailure('Failed to collect all sources')
        })
    }

    function collectSource(source) {
      collectOSINTSSource(source.id)
        .then(() => {
          notifySuccess(`Successfully collected ${source.name}`)
        })
        .catch(() => {
          notifyFailure(`Failed to collect ${source.name}`)
        })
    }

    function previewSource(source) {
      previewOSINTSSource(source.id)
        .then(() => {
          router.push({
            name: 'osint_sources_preview',
            params: { source_id: source.id }
          })
        })
        .catch(() => {
          notifyFailure(`Failed to preview ${source.name}`)
        })
    }

    async function toggleState(source) {
      await configStore.toggleOSINTSSourceState(source)
    }

    return {
      parameters,
      collector_options,
      osint_sources,
      selected,
      formData,
      editTitle,
      showForm,
      showDeletePopup,
      showExportPopup,
      sourceTotalCount: configStore.osint_sources.total_count - 1,
      itemToDelete,
      formFormat,
      updateData,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      createItem,
      updateItem,
      importData,
      collectSource,
      previewSource,
      forceDeleteItem,
      collectAllSources,
      loadDefaultSources,
      toggleState,
      selectionChange
    }
  }
}
</script>
