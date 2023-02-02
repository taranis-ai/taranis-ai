<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="presets"
      :headerFilter="['tag', 'id', 'name', 'description']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :configData="formData"
      :formFormat.sync="formFormat"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable'
import EditConfig from '../../components/config/EditConfig'
import {
  deletePublisherPreset,
  createPublisherPreset,
  updatePublisherPreset
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, parseParameterValues, createParameterValues, objectFromFormat, notifyFailure } from '@/utils/helpers'

export default {
  name: 'presets',
  components: {
    DataTable,
    EditConfig
  },
  data: () => ({
    presets: [],
    formData: {},
    parameters: {},
    publishers: [],
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
          name: 'publisher_id',
          label: 'Type',
          type: 'select',
          required: true,
          options: this.publishers,
          disabled: this.edit
        }
      ]
      if (this.parameters[this.formData.publisher_id]) {
        return base.concat(this.parameters[this.formData.publisher_id])
      }
      return base
    }
  },
  methods: {
    ...mapActions('config', ['loadPublisherPresets', 'loadPublishers']),
    ...mapGetters('config', ['getPublisherPresets', 'getPublishers']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadPublisherPresets().then(() => {
        const sources = this.getPublisherPresets()
        this.presets = parseParameterValues(sources.items)
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
      this.loadPublishers().then(() => {
        const publishers = this.getPublishers()
        this.publishers = publishers.items.map(publisher => {
          this.parameters[publisher.id] = publisher.parameters.map(parameter => {
            return {
              name: parameter.key,
              label: parameter.name,
              type: 'text'
            }
          })
          return {
            value: publisher.id,
            text: publisher.name
          }
        })
      })
    },
    addItem() {
      this.formData = objectFromFormat(this.formFormat)
      this.edit = false
    },
    editItem(item) {
      this.formData = item
      this.edit = true
    },
    handleSubmit(submittedData) {
      delete submittedData.parameter_values
      const parameter_list = this.parameters[this.formData.publisher_id].map(item => item.name)
      const updateItem = createParameterValues(parameter_list, submittedData)
      if (this.edit) {
        this.updateItem(updateItem)
      } else {
        this.createItem(updateItem)
      }
    },
    deleteItem(item) {
      if (!item.default) {
        deletePublisherPreset(item).then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        }).catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
      }
    },
    createItem(item) {
      createPublisherPreset(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updatePublisherPreset(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to update ${item.name}`)
      })
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
