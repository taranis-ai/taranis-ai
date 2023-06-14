import { getAllProducts } from '@/api/publish'
import { getAllUserPublishersPresets } from '@/api/user'
import { useFilterStore } from './FilterStore'
import { defineStore } from 'pinia'

export const usePublishStore = defineStore('publish', {
  state: () => ({
    products: { total_count: 0, items: [] },
    products_publisher_presets: { total_count: 0, items: [] }
  }),
  actions: {
    async loadProducts(data) {
      const response = await getAllProducts(data)
      this.products = response.data
    },
    async updateProducts() {
      const filter = useFilterStore()
      const response = await getAllProducts(filter.productFilter)
      this.products = response.data
    },
    async loadUserPublishersPresets(context, data) {
      const response = await getAllUserPublishersPresets(data)
      this.products_publisher_presets = response.data
    }
  }
})
