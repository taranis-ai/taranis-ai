<template>
  <div>
    <DataTable
      v-model:items="word_lists.items"
      :add-button="true"
      :header-filter="['tag', 'name', 'description']"
      sort-by-item="id"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @selection-change="selectionChange"
      @update-items="updateData"
    >
      <template #titlebar>
        <ImportExport @import="importData" @export="exportData"></ImportExport>
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
      @submit="handleSubmit"
    ></EditConfig>
  </div>
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
        name: 'use_for_stop_words',
        label: 'Use for stop words',
        type: 'switch'
      },
      {
        name: 'entries',
        label: 'Words',
        type: 'list'
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

    const handleSubmit = (submittedData) => {
      console.log(submittedData)
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
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
      importWordList(data)
    }

    const exportData = () => {
      exportWordList(selected.value)
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection.map((item) => item.id)
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
      edit,
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
