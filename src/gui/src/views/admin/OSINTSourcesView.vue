<template>
  <v-container fluid>
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
        <ImportExport @import="importData" @export="exportData" />
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
        :title="`Delete Source ${itemToDelete.name}?`"
        message="Delete the source and all gathered News Items permanently."
        @delete-item="forceDeleteItem(itemToDelete)"
        @close="showDeletePopup = false"
      />
    </v-dialog>
  </v-container>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import ImportExport from '@/components/config/ImportExport.vue'
import PopupDeleteItem from '@/components/popups/PopupDeleteItem.vue'
import {
  deleteOSINTSource,
  createOSINTSource,
  updateOSINTSource,
  exportOSINTSources,
  importOSINTSources,
  collectOSINTSSource,
  previewOSINTSSource,
  collectAllOSINTSSources
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
    PopupDeleteItem
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

    const updateData = () => {
      configStore.loadOSINTSources().then(() => {
        mainStore.itemCountFiltered = configStore.osint_sources.items.length - 1
        mainStore.itemCountTotal = configStore.osint_sources.total_count - 1
      })
      configStore.loadWorkerTypes().then(() => {
        collector_options.value = collector_types.value.map((collector) => {
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

    const createItem = (item) => {
      createOSINTSource(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updateOSINTSource(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    }

    const importData = (data) => {
      importOSINTSources(data)
        .then(() => {
          notifySuccess(`Successfully imported ${data.get('file').name}`)
          setTimeout(updateData(), 1000)
        })
        .catch(() => {
          notifyFailure('Failed to import')
        })
    }

    const exportData = () => {
      let queryString = ''
      if (selected.value.length > 0) {
        queryString = 'ids=' + selected.value.join('&ids=')
      }
      exportOSINTSources(queryString)
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    const collectAllSources = () => {
      collectAllOSINTSSources()
        .then(() => {
          notifySuccess('Successfully collected all sources')
        })
        .catch(() => {
          notifyFailure('Failed to collect all sources')
        })
    }

    const collectSource = (source) => {
      collectOSINTSSource(source.id)
        .then(() => {
          notifySuccess(`Successfully collected ${source.name}`)
        })
        .catch(() => {
          notifyFailure(`Failed to collect ${source.name}`)
        })
    }

    const previewSource = (source) => {
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

    return {
      parameters,
      collector_options,
      osint_sources,
      selected,
      formData,
      editTitle,
      showForm,
      showDeletePopup,
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
      exportData,
      collectSource,
      previewSource,
      forceDeleteItem,
      collectAllSources,
      selectionChange
    }
  }
}
</script>
