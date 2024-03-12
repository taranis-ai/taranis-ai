import { getAllProducts, getAllProductTypes, getProduct } from '@/api/publish'
import { useFilterStore } from './FilterStore'
import { defineStore } from 'pinia'

export const usePublishStore = defineStore('publish', {
  state: () => ({
    products: { total_count: 0, items: [] },
    product_types: { total_count: 0, items: [] }
  }),
  actions: {
    async loadProducts(data) {
      const response = await getAllProducts(data)
      this.products = response.data
    },
    async loadProductTypes(data) {
      const response = await getAllProductTypes(data)
      this.product_types = response.data
    },
    async updateProductByID(product_id) {
      const response = await getProduct(product_id)
      const updated_item = response.data
      let found = false

      this.products.items = this.products.items.map((item) => {
        if (item.id === product_id) {
          found = true
          return { ...item, ...updated_item }
        }
        return item
      })

      if (!found) {
        this.products.items.push(updated_item)
      }
    },
    async updateProducts() {
      const filter = useFilterStore()
      const response = await getAllProducts(filter.productFilter)
      this.products = response.data
    },
    sseProductRendered(data) {
      console.debug('Triggerd product rendered: ' + data)
      this.updateProductByID(data.id)
    }
  },
  persist: {
    paths: ['product_types']
  }
})
