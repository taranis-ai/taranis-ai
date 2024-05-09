import {
  getAllProducts,
  getAllProductTypes,
  getProduct,
  getRenderdProduct,
  updateProduct
} from '@/api/publish'
import { useFilterStore } from './FilterStore'
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

    async function loadProducts(data) {
      const response = await getAllProducts(data)
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
      const response = await getAllProducts(filter.productFilterQuery)
      products.value = response.data
    }

    function sseProductRendered(data) {
      console.log('Product rendered:', data)
      loadRenderedProduct(data.id)
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
      sseProductRendered
    }
  },
  {
    persist: ['products', 'product_types']
  }
)
