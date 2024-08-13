<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Wordlists Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-2">
        <DataTable
          v-model:items="word_lists.items"
          :add-button="true"
          :header-filter="['name', 'description', 'usage', 'actions']"
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
            />
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
        <WordListForm
          v-if="showForm"
          :wordlist-id="word_list_id"
          @submit="handleSubmit"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { ref, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import WordListForm from '@/components/config/WordListForm.vue'
import ImportExport from '@/components/config/ImportExport.vue'
import {
  deleteWordList,
  createWordList,
  updateWordList,
  exportWordList,
  importWordList,
  gatherWordListEntries
} from '@/api/config'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'WordLists',
  components: {
    DataTable,
    ImportExport,
    WordListForm
  },
  setup() {
    const showForm = ref(false)
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const selected = ref([])
    const word_list_id = ref(0)
    const { word_lists } = storeToRefs(configStore)

    const updateData = () => {
      configStore.loadWordLists().then(() => {
        mainStore.itemCountTotal = word_lists.value.total_count
        mainStore.itemCountFiltered = word_lists.value.items.length
      })
    }

    const addItem = () => {
      showForm.value = true
    }

    const editItem = (item) => {
      word_list_id.value = item.id
      showForm.value = true
    }

    const handleSubmit = (submittedData) => {
      delete submittedData.entries

      updateItem(submittedData)

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
      word_list_id,
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
