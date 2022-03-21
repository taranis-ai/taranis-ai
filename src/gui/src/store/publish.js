import { getAllProducts } from '@/api/publish'
import { getAllUserPublishersPresets } from '@/api/user'

const state = {
  products: { total_count: 0, items: [] },
  products_publisher_presets: { total_count: 0, items: [] }
}

const actions = {

  getAllProducts (context, data) {
    return getAllProducts(data)
      .then(response => {
        context.commit('setProducts', response.data)
      })
  },

  getAllUserPublishersPresets (context, data) {
    return getAllUserPublishersPresets(data)
      .then(response => {
        context.commit('setProductsPublisherPresets', response.data)
      })
  }
}

const mutations = {

  setProducts (state, new_product) {
    state.products = new_product
  },

  setProductsPublisherPresets (state, new_publisher_presets) {
    state.products_publisher_presets = new_publisher_presets
  }
}

const getters = {

  getProducts (state) {
    return state.products
  },

  getProductsPublisherPresets (state) {
    return state.products_publisher_presets
  }
}

export const publish = {
  state,
  actions,
  mutations,
  getters
}
