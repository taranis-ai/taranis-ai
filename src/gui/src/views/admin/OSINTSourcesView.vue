<template>
  <div>
    <DataTable
      :items="sources"
      :add-button="true"
      :header-filter="['tag', 'state', 'name']"
      sort-by-item="id"
      :action-column="true"
      tag-icon="mdi-animation-outline"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
      @selection-change="selectionChange"
    >
      <template #titlebar>
        <ImportExport @import="importData" @export="exportData"></ImportExport>
        <v-btn
          color="blue-grey"
          dark
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
      </template>
    </DataTable>
    <EditConfig
      v-if="showForm"
      :config-data="formData"
      :form-format="formFormat"
      :parameters="parameters"
      :title="editTitle"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import ImportExport from '@/components/config/ImportExport.vue'
import {
  deleteOSINTSource,
  createOSINTSource,
  updateOSINTSource,
  exportOSINTSources,
  importOSINTSources,
  collectOSINTSSource,
  collectAllOSINTSSources
} from '@/api/config'
import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'
import { storeToRefs } from 'pinia'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { ref, computed, onMounted } from 'vue'

export default {
  name: 'OSINTSourcesView',
  components: {
    DataTable,
    EditConfig,
    ImportExport
  },
  setup() {
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const { collector_types, osint_sources, word_lists, parameters } =
      storeToRefs(configStore)

    const sources = ref([])
    const collector_options = ref([])
    const selected = ref([])
    const formData = ref({})
    const edit = ref(false)
    const showForm = ref(false)

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
          rules: [(v) => !!v || 'Required']
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea'
        },
        {
          name: 'word_lists',
          label: 'Word Lists',
          type: 'table',
          headers: [
            { title: 'Name', key: 'name' },
            { title: 'Description', key: 'description' },
            { title: 'ID', key: 'id' }
          ],
          items: word_lists.value.items
        },
        {
          name: 'type',
          label: 'Collector',
          type: 'select',
          items: collector_options.value
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
        sources.value = osint_sources.value.items
        mainStore.itemCountFiltered = osint_sources.value.items.length
        mainStore.itemCountTotal = osint_sources.value.total_count
      })
      configStore.loadWorkerTypes().then(() => {
        collector_options.value = collector_types.value.map((collector) => {
          return {
            value: collector.type,
            title: collector.name
          }
        })
      })
      configStore.loadWordLists()
      configStore.loadParameters()
    }

    onMounted(() => {
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

    const deleteItem = (item) => {
      deleteOSINTSource(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
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

    return {
      sources,
      parameters,
      collector_options,
      selected,
      formData,
      editTitle,
      showForm,
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
      collectAllSources,
      selectionChange
    }
  }
}
</script>
