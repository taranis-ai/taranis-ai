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
          <template #nodata>
            <v-empty-state
              icon="mdi-magnify"
              title="No word lists Found"
              class="my-5"
            >
              <v-btn
                text="refresh"
                prepend-icon="mdi-refresh"
                @click.stop="updateData"
              />
              <v-btn
                v-if="wordListTotalCount === 0"
                text="load default lists"
                prepend-icon="mdi-database"
                @click.stop="loadDefaultWordLists"
              />
            </v-empty-state>
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
  exportWordList,
  importWordList,
  gatherWordListEntries
} from '@/api/config'

import { getDefaultWordLists } from '@/api/static'
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

    function updateData() {
      configStore.loadWordLists().then(() => {
        mainStore.itemCountTotal = word_lists.value.total_count
        mainStore.itemCountFiltered = word_lists.value.items.length
      })
    }

    function addItem() {
      showForm.value = true
    }

    function editItem(item) {
      word_list_id.value = item.id
      showForm.value = true
    }

    function handleSubmit() {
      updateData()
      showForm.value = false
    }

    async function deleteItem(item) {
      try {
        await deleteWordList(item)
        notifySuccess(`Successfully deleted ${item.name}`)
        updateData()
      } catch (error) {
        notifyFailure(`Failed to delete ${item.name}`)
      }
    }

    async function updateWordListEntries(item) {
      try {
        await gatherWordListEntries(item)
        notifySuccess(`Triggered update for ${item.name}`)
      } catch (error) {
        notifyFailure(`Failed to trigger update for ${item.name}`)
      }
    }

    async function importData(data) {
      try {
        await importWordList(data)
        notifySuccess('Successfully imported data')
        updateData()
      } catch (error) {
        // Handle error
      }
    }

    async function loadDefaultWordLists() {
      try {
        const response = await getDefaultWordLists()
        const file = response.data
        const formData = new FormData()
        formData.append('file', file, 'default_word_list.json')
        await importData(formData)
      } catch (error) {
        notifyFailure(`Failed to import default word list: ${error.message}`)
      }
    }

    function exportData() {
      let queryString = ''
      if (selected.value.length > 0) {
        queryString = 'ids=' + selected.value.join('&ids=')
      }
      exportWordList(queryString)
    }

    function selectionChange(new_selection) {
      selected.value = new_selection
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
      wordListTotalCount: configStore.word_lists.total_count,
      deleteItem,
      importData,
      exportData,
      selectionChange,
      updateWordListEntries,
      loadDefaultWordLists
    }
  }
}
</script>
