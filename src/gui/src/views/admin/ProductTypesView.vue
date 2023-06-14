<template>
  <div>
    <DataTable
      v-model:items="productTypes"
      :add-button="true"
      :header-filter="['tag', 'id', 'title', 'description']"
      sort-by-item="id"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="formData && Object.keys(formData).length > 0"
      :form-format="formFormat"
      :config-data="formData"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import {
  deleteProductType,
  createProductType,
  updateProductType
} from '@/api/config'
import {
  notifySuccess,
  notifyFailure,
  parseParameterValues,
  createParameterValues,
  objectFromFormat
} from '@/utils/helpers'
import { mapActions, mapState, mapWritableState } from 'pinia'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'

export default {
  name: 'ProductTypesView',
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
    ...mapState(useConfigStore, {
      store_product_types: 'product_types',
      store_presenters: 'presenters'
    }),
    ...mapWritableState(useMainStore, ['itemCountTotal', 'itemCountFiltered']),
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
    },
    xxx() {
      return objectFromFormat(this.formFormat)
    }
  },
  mounted() {
    this.updateData()
  },
  methods: {
    ...mapActions(useConfigStore, ['loadProductTypes', 'loadPresenters']),
    updateData() {
      this.loadProductTypes().then(() => {
        const sources = this.store_product_types
        this.productTypes = parseParameterValues(sources.items)
        this.itemCountFiltered = sources.length
        this.itemCountTotal = sources.total_count
      })
      this.loadPresenters().then(() => {
        const presenters = this.store_presenters
        this.presenters = presenters.items.map((presenter) => {
          this.parameters[presenter.id] = presenter.parameters.map(
            (parameter) => {
              return {
                name: parameter.key,
                label: parameter.name,
                type: 'text'
              }
            }
          )
          return {
            value: presenter.id,
            title: presenter.name
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
      console.debug('submittedData', submittedData)
      delete submittedData.parameter_values
      const parameter_list = this.parameters[this.formData.presenter_id].map(
        (item) => item.name
      )
      const updateItem = createParameterValues(parameter_list, submittedData)
      if (this.edit) {
        this.updateItem(updateItem)
      } else {
        this.createItem(updateItem)
      }
    },
    deleteItem(item) {
      if (!item.default) {
        deleteProductType(item)
          .then(() => {
            notifySuccess(`Successfully deleted ${item.name}`)
            this.updateData()
          })
          .catch(() => {
            notifyFailure(`Failed to delete ${item.name}`)
          })
      }
    },
    createItem(item) {
      createProductType(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    },
    updateItem(item) {
      updateProductType(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    }
  }
}
</script>
