<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="productTypes"
      :headerFilter="['tag', 'id', 'name', 'description']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
    />
    <NewProductType
      @submit="handleSubmit"
    ></NewProductType>
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import NewProductType from '@/components/config/product_types/NewProductType'
import {
  deleteProductType,
  createProductType,
  updateProductType
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'Organizations',
  components: {
    ConfigTable,
    NewProductType
  },
  data: () => ({
    productTypes: [],
    formData: {},
    edit: false,
    product: {
      id: -1,
      title: '',
      description: '',
      presenter_id: '',
      parameter_values: []
    }
  }),
  methods: {
    ...mapActions('config', ['loadProductTypes']),
    ...mapGetters('config', ['getProductTypes']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadProductTypes().then(() => {
        const sources = this.getProductTypes()
        this.productTypes = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
    },
    addItem() {
      this.formData = this.product
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
