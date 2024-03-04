import { getAllProducts, getAllProductTypes } from '@/api/publish'
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
    async updateProducts() {
      const filter = useFilterStore()
      const response = await getAllProducts(filter.productFilter)
      this.products = response.data
    }
  },
  persist: {
    paths: ['product_types']
  }
})
