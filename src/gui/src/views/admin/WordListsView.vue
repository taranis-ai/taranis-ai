<template>
  <v-container fluid>
    <DataTable
      v-model:items="word_lists.items"
      :add-button="true"
      :header-filter="['tag', 'name', 'description', 'usage', 'actions']"
      tag-icon="mdi-format-list-bulleted-square"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @selection-change="selectionChange"
      @update-items="updateData"
    >
      <template #titlebar>
        <ImportExport
          accepts="application/json, text/csv"
          @import="importData"
          @export="exportData"
        ></ImportExport>
      </template>
      <template #actionColumn="source">
        <v-tooltip left>
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              color="secondary"
              icon="mdi-update"
              @click.stop="updateWordListEntries(source.item)"
            />
          </template>
          <span>Update Wordlist</span>
        </v-tooltip>
      </template>
    </DataTable>
    <EditConfig
      v-if="showForm"
      :config-data="formData"
      :form-format="formFormat"
      :title="editTitle"
      @submit="handleSubmit"
    ></EditConfig>
  </v-container>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import ImportExport from '@/components/config/ImportExport.vue'
import {
  deleteWordList,
  createWordList,
  updateWordList,
  exportWordList,
  importWordList,
  gatherWordListEntries
} from '@/api/config'
import { notifySuccess, objectFromFormat, notifyFailure } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'WordLists',
  components: {
    DataTable,
    EditConfig,
    ImportExport
  },
  setup() {
    const showForm = ref(false)
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const selected = ref([])
    const formData = ref({})
    const edit = ref(false)
    const { word_lists } = storeToRefs(configStore)

    const formFormat = computed(() => [
      {
        name: 'id',
        label: 'ID',
        type: 'text',
        disabled: true
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
        type: 'textarea',
        rules: [(v) => !!v || 'Required']
      },
      {
        name: 'link',
        label: 'Link',
        type: 'text'
      },
      {
        name: 'usage',
        label: 'Usage',
        type: 'checkbox',
        items: [
          { value: 'COLLECTOR_WHITELIST', label: 'Collector Whitelist' },
          { value: 'COLLECTOR_BLACKLIST', label: 'Collector Blacklist' },
          { value: 'TAGGING_BOT', label: 'Tagging Bot' }
        ]
      },
      {
        name: 'entries',
        label: 'Words',
        type: 'table',
        headers: [
          { title: 'Word', key: 'value' },
          { title: 'Description', key: 'description' }
        ],
        groupBy: [{ key: 'category', order: 'asc' }],
        disabled: true
      }
    ])

    const updateData = () => {
      configStore.loadWordLists().then(() => {
        mainStore.itemCountTotal = word_lists.value.total_count
        mainStore.itemCountFiltered = word_lists.value.items.length
      })
    }

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
        ? `Edit Wordlist: '${formData.value['name']}'`
        : 'Add Wordlist'
    })

    const parse_usage = (usage) => {
      if (!usage || usage.length === 0) {
        notifyFailure('Usage must contain at least one value')
        return false
      }

      if (
        usage.includes('COLLECTOR_WHITELIST') &&
        usage.includes('COLLECTOR_BLACKLIST')
      ) {
        notifyFailure('Whitelist and Blacklist are mutually exclusive')
        return false
      }
      if (
        usage.includes('COLLECTOR_BLACKLIST') &&
        usage.includes('TAGGING_BOT')
      ) {
        notifyFailure('Blacklist and Tagging Bot are mutually exclusive')
        return false
      }
      return true
    }

    const handleSubmit = (submittedData) => {
      delete submittedData.entries
      if (!parse_usage(submittedData.usage)) {
        return
      }

      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    const deleteItem = (item) => {
      deleteWordList(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    }

    const createItem = (item) => {
      createWordList(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updateWordList(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    }

    const importData = (data) => {
      importWordList(data).then(() => {
        notifySuccess('Successfully imported data')
        updateData()
      })
    }

    const exportData = () => {
      console.debug(`Exporting ${selected.value.join('&ids=')}`)
      let queryString = ''
      if (selected.value.length > 0) {
        queryString = 'ids=' + selected.value.join('&ids=')
      }
      exportWordList(queryString)
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    const updateWordListEntries = (item) => {
      gatherWordListEntries(item)
        .then(() => {
          notifySuccess(`Triggered update for ${item.name}`)
        })
        .catch(() => {
          notifyFailure(`Failed to trigger update for ${item.name}`)
        })
    }

    onMounted(() => {
      updateData()
    })

    return {
      selected,
      formData,
      formFormat,
      editTitle,
      word_lists,
      showForm,
      updateData,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      createItem,
      updateItem,
      importData,
      exportData,
      selectionChange,
      updateWordListEntries
    }
  }
}
</script>
