import {
  getAllProducts,
  getAllProductTypes,
  getProduct,
  getRenderdProduct,
  deleteProduct,
  updateProduct
} from '@/api/publish'
import { useFilterStore } from './FilterStore'
import { useMainStore } from './MainStore'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notifyFailure, notifySuccess } from '@/utils/helpers'

export const usePublishStore = defineStore(
  'publish',
  () => {
    const products = ref({ total_count: 0, items: [] })
    const product_types = ref({ total_count: 0, items: [] })
    const renderedProduct = ref(null)
    const renderedProductMimeType = ref(null)

    async function loadProducts() {
      const response = await getAllProducts()
      products.value = response.data
    }
    async function loadProductTypes(data) {
      const response = await getAllProductTypes(data)
      product_types.value = response.data
    }
    async function updateProductByID(product_id) {
      const response = await getProduct(product_id)
      const updated_item = response.data
      let found = false

      products.value.items = products.value.items.map((item) => {
        if (item.id === product_id) {
          found = true
          return { ...item, ...updated_item }
        }
        return item
      })

      if (!found) {
        products.value.items.push(updated_item)
      }
    }

    async function loadRenderedProduct(product_id) {
      const response = await getRenderdProduct(product_id)
      renderedProduct.value = response.data
      renderedProductMimeType.value = response.headers['content-type']
    }

    async function patchProduct(product) {
      let updated_item = null
      try {
        const response = await updateProduct(product)
        notifySuccess('Product updated')
        updated_item = response.data
      } catch (error) {
        notifyFailure('Failed to update product')
      }

      let found = false

      products.value.items = products.value.items.map((item) => {
        if (item.id === product.id) {
          found = true
          return { ...item, ...updated_item }
        }
        return item
      })

      if (!found) {
        products.value.items.push(updated_item)
      }
    }

    async function updateProducts() {
      const filter = useFilterStore()
      const mainStore = useMainStore()
      try {
        const response = await getAllProducts(filter.productFilterQuery)
        products.value = response.data
        mainStore.itemCountTotal = products.value.total_count
        mainStore.itemCountFiltered = products.value.items.length
      } catch (error) {
        products.value = { total_count: 0, items: [] }
        notifyFailure(error)
      }
    }

    async function removeProduct(product) {
      const product_id = product.id || product
      try {
        const response = await deleteProduct(product_id)
        products.value.items = products.value.items.filter(
          (item) => item.id !== product_id
        )
        notifySuccess(response.data.message)
      } catch (error) {
        notifyFailure(error)
      }
    }

    function sseProductRendered(data) {
      console.log('Product rendered:', data)
      loadRenderedProduct(data.id)
    }

    function reset() {
      products.value = { total_count: 0, items: [] }
      product_types.value = { total_count: 0, items: [] }
      renderedProduct.value = null
      renderedProductMimeType.value = null
    }

    return {
      products,
      product_types,
      renderedProduct,
      renderedProductMimeType,
      patchProduct,
      loadProducts,
      loadProductTypes,
      updateProductByID,
      loadRenderedProduct,
      updateProducts,
      removeProduct,
      sseProductRendered,
      reset
    }
  },
  {
    persist: ['products', 'product_types']
  }
)
