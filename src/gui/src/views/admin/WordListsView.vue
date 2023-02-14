<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="word_lists"
      :headerFilter="['tag', 'name', 'description']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @selection-change="selectionChange"
      @update-items="updateData"
    >
    <template v-slot:titlebar>
      <ImportExport
        @import="importData"
        @export="exportData"
      ></ImportExport>
    </template>
    </DataTable>
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :configData="formData"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable'
import EditConfig from '../../components/config/EditConfig'
import ImportExport from '../../components/config/ImportExport'
import {
  deleteWordList,
  createWordList,
  updateWordList,
  exportWordList,
  importWordList
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, emptyValues, notifyFailure } from '@/utils/helpers'

export default {
  name: 'WordLists',
  components: {
    DataTable,
    EditConfig,
    ImportExport
  },
  data: () => ({
    word_lists: [],
    selected: [],
    formData: {},
    edit: false
  }),
  methods: {
    ...mapActions('config', ['loadWordLists']),
    ...mapGetters('config', ['getWordLists']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadWordLists().then(() => {
        const sources = this.getWordLists()
        this.word_lists = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
    },
    addItem() {
      this.formData = emptyValues(this.word_lists[0])
      this.edit = false
    },
    editItem(item) {
      this.formData = item
      this.edit = true
    },
    handleSubmit(submittedData) {
      console.log(submittedData)
      if (this.edit) {
        this.updateItem(submittedData)
      } else {
        this.createItem(submittedData)
      }
    },
    deleteItem(item) {
      deleteWordList(item).then(() => {
        notifySuccess(`Successfully deleted ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to delete ${item.name}`)
      })
    },
    createItem(item) {
      createWordList(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updateWordList(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to update ${item.name}`)
      })
    },
    importData(data) {
      importWordList(data)
    },
    exportData() {
      console.debug('export OSINT sources')
      exportWordList(this.selected)
    },
    selectionChange(selected) {
      this.selected = selected.map(item => item.id)
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
