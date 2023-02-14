<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="osint_sources"
      :headerFilter="['tag', 'name', 'description', 'FEED_URL']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
      @selection-change="selectionChange"
    >
      <template v-slot:titlebar>
        <ImportExport @import="importData" @export="exportData"></ImportExport>
      </template>
    </DataTable>
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :configData.sync="formData"
      :formFormat.sync="formFormat"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable'
import EditConfig from '../../components/config/EditConfig'
import ImportExport from '../../components/config/ImportExport'
import {
  deleteOSINTSource,
  createOSINTSource,
  updateOSINTSource,
  exportOSINTSources,
  importOSINTSources
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import {
  notifySuccess,
  objectFromFormat,
  notifyFailure,
  parseParameterValues,
  createParameterValues
} from '@/utils/helpers'

export default {
  name: 'OSINTSources',
  components: {
    DataTable,
    EditConfig,
    ImportExport
  },
  data: () => ({
    osint_sources: [],
    parameters: {},
    selected: [],
    formData: {},
    collectors: [],
    edit: false
  }),
  computed: {
    formFormat() {
      const base = [
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
          required: true
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          required: true
        },
        {
          name: 'collector_id',
          label: 'Collector',
          type: 'select',
          options: this.collectors
        }
      ]
      if (this.parameters[this.formData.collector_id]) {
        return base.concat(this.parameters[this.formData.collector_id])
      }
      return base
    }
  },
  methods: {
    ...mapActions('config', ['loadOSINTSources', 'loadCollectors']),
    ...mapGetters('config', ['getOSINTSources', 'getCollectors']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadOSINTSources().then(() => {
        const sources = this.getOSINTSources()
        this.osint_sources = parseParameterValues(sources.items)
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
      this.loadCollectors().then(() => {
        const collectors = this.getCollectors()
        this.collectors = collectors.items.map((collector) => {
          this.parameters[collector.id] = collector.parameters.map(
            (parameter) => {
              return {
                name: parameter.key,
                label: parameter.name,
                type: 'text'
              }
            }
          )
          return {
            value: collector.id,
            text: collector.name
          }
        })
      })
    },

    addItem() {
      console.debug(this.formFormat)
      this.formData = objectFromFormat(this.formFormat)
      this.edit = false
    },
    editItem(item) {
      this.formData = item
      this.edit = true
    },
    handleSubmit(submittedData) {
      delete submittedData.parameter_values
      const parameter_list = this.parameters[this.formData.collector_id].map(
        (item) => item.name
      )
      const updateItem = createParameterValues(parameter_list, submittedData)
      console.debug('createParameterValues', updateItem)
      if (this.edit) {
        this.updateItem(updateItem)
      } else {
        this.createItem(updateItem)
      }
    },
    deleteItem(item) {
      deleteOSINTSource(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    },
    createItem(item) {
      createOSINTSource(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    },
    updateItem(item) {
      updateOSINTSource(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    },
    importData(data) {
      importOSINTSources(data)
        .then(() => {
          notifySuccess(`Successfully imported ${data.get('file').name}`)
          setTimeout(this.updateData(), 1000)
        })
        .catch(() => {
          notifyFailure('Failed to import')
        })
    },
    exportData() {
      const queryString = 'ids=' + this.selected.join('&ids=')
      exportOSINTSources(queryString)
    },
    selectionChange(selected) {
      this.selected = selected.map((item) => item.id)
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
