<template>
  <div>
    <DataTable
      :addButton="true"
      :items.sync="productTypes"
      :headerFilter="['tag', 'id', 'title', 'description']"
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
import EditConfig from '@/components/config/EditConfig'
import {
  deleteProductType,
  createProductType,
  updateProductType
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure, parseParameterValues, createParameterValues, objectFromFormat } from '@/utils/helpers'

export default {
  name: 'Organizations',
  components: {
    DataTable,
    EditConfig
  },
  data: () => ({
    productTypes: [],
    formData: {},
    edit: false,
    parameters: {},
    selected: [],
    presenters: []
  }),
  computed: {
    formFormat() {
      const base = [
        {
          name: 'id',
          label: 'ID',
          type: 'number',
          disabled: true
        },
        {
          name: 'title',
          label: 'Title',
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
          name: 'presenter_id',
          label: 'Presenter',
          type: 'select',
          required: true,
          options: this.presenters,
          disabled: this.edit
        }
      ]
      if (this.parameters[this.formData.presenter_id]) {
        return base.concat(this.parameters[this.formData.presenter_id])
      }
      return base
    }
  },
  methods: {
    ...mapActions('config', ['loadProductTypes', 'loadPresenters']),
    ...mapGetters('config', ['getProductTypes', 'getPresenters']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadProductTypes().then(() => {
        const sources = this.getProductTypes()
        this.productTypes = parseParameterValues(sources.items)
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
      this.loadPresenters().then(() => {
        const presenters = this.getPresenters()
        this.presenters = presenters.items.map(presenter => {
          this.parameters[presenter.id] = presenter.parameters.map(parameter => {
            return {
              name: parameter.key,
              label: parameter.name,
              type: 'text'
            }
          })
          return {
            value: presenter.id,
            text: presenter.name
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
      const parameter_list = this.parameters[this.formData.presenter_id].map(item => item.name)
      const updateItem = createParameterValues(parameter_list, submittedData)
      if (this.edit) {
        this.updateItem(updateItem)
      } else {
        this.createItem(updateItem)
      }
    },
    deleteItem(item) {
      if (!item.default) {
        deleteProductType(item).then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        }).catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
      }
    },
    createItem(item) {
      createProductType(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      }).catch(() => {
        notifyFailure(`Failed to create ${item.name}`)
      })
    },
    updateItem(item) {
      updateProductType(item).then(() => {
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
