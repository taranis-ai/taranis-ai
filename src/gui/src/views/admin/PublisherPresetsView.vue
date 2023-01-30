<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="presets"
      :headerFilter="['tag', 'id', 'name', 'description']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
    />
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :configData="formData"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import EditConfig from '../../components/config/EditConfig'
import {
  deletePublisherPreset,
  createPublisherPreset,
  updatePublisherPreset
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, parseParameterValues, objectFromFormat, notifyFailure } from '@/utils/helpers'

export default {
  name: 'presets',
  components: {
    ConfigTable,
    EditConfig
  },
  data: () => ({
    presets: [],
    unparsed_presets: [],
    formData: {},
    parameters: {},
    presets_types: [],
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
          disabled: true
        },
        {
          name: 'description',
          label: 'Description',
          type: 'textarea',
          disabled: true
        },
        {
          name: 'type',
          label: 'Type',
          type: 'select',
          required: true,
          options: this.presets_types,
          disabled: this.edit
        }
      ]
      if (this.parameters[this.formData.type]) {
        return base.concat(this.parameters[this.formData.type])
      }
      return base
    }
  },
  methods: {
    ...mapActions('config', ['loadPublisherPresets']),
    ...mapGetters('config', ['getPublisherPresets']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadPublisherPresets().then(() => {
        const sources = this.getPublisherPresets()
        this.unparsed_presets = sources.items
        this.presets = parseParameterValues(sources.items)

        this.presets_types = sources.items.map(item => {
          this.parameters[item.type] = item.parameter_values.map(param => {
            return {
              name: param.parameter.key,
              label: param.parameter.key,
              type: 'text'
            }
          })
          return item.type
        })
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
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
      console.log(submittedData)
      if (this.edit) {
        this.updateItem(submittedData)
      } else {
        this.createItem(submittedData)
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
